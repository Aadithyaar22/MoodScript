"""Redesigned arbitration: use the LLM for linguistic judgement, not classification.

WHY THE ORIGINAL FAILS
----------------------
The deployed arbiter is handed a conflict and asked to name the emotion. On exactly
those conflict cases the text signal is worth ~17% accuracy, so the model is being
asked to perform the task it is weakest at, using the weaker of the two signals, and
it cannot see the face image at all — only the face model's label. It also always
answers, so every uncertain guess is an opportunity to break a case numeric fusion
had right.

THE REFRAME
-----------
Language models are poor at fine-grained 7-way affect classification but genuinely
good at meta-linguistic judgement: is this sarcastic, negated, understated, vague,
or does it state feeling plainly? So do not ask the LLM WHICH emotion it is. Ask it
HOW MUCH THE TEXT CAN BE TRUSTED, and feed that into the fusion weight.

Designs compared (all on the same conflict cases, same ground truth):
  A  deployed          — LLM names the emotion (7-way)
  B  informed binary   — LLM picks text or face, but is TOLD the historical
                         reliability of each, so its prior is correct
  C  abstaining binary — B, but only overrides when it reports high confidence
  D  trust-weighted    — LLM scores how literally the text means what it says;
                         that score scales the text weight inside v2 fusion.
                         The LLM never picks an emotion.

Baselines: always-face, v2 fusion, and the oracle ceiling for a perfect chooser.
"""
import argparse
import asyncio
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from models.fusion import FusionLayer  # noqa: E402

UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
IDX = {e: i for i, e in enumerate(UNIFIED)}
K = len(UNIFIED)
_HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "llama-3.1-8b-instant"
EPS = 1e-12


def vec(d):
    v = np.array([d[e] for e in UNIFIED], float)
    s = v.sum()
    return v / s if s > 0 else np.full(K, 1 / K)


def ts(P, T):
    l = np.log(np.clip(P, EPS, 1)) / T
    l -= l.max(1, keepdims=True)
    e = np.exp(l)
    return e / e.sum(1, keepdims=True)


def fitT(P, y):
    from scipy.optimize import minimize_scalar
    def nll(T):
        if T <= 0:
            return 1e9
        return float(-np.mean(np.log(np.clip(ts(P, T)[np.arange(len(y)), y], EPS, 1))))
    return float(minimize_scalar(nll, bounds=(0.05, 20), method="bounded").x)


def class_reliability(P, y, smoothing=5.0):
    pred = P.argmax(1)
    overall = float((pred == y).mean())
    r = np.zeros(K)
    for c in range(K):
        m = pred == c
        n = int(m.sum())
        hits = float((y[m] == c).sum()) if n else 0.0
        r[c] = (hits + smoothing * overall) / (n + smoothing)
    return r


def fuse_v2(A, B, rel_t, rel_f, text_scale=None):
    """v2 fusion; text_scale optionally modulates the text weight per sample (design D)."""
    at = (rel_t[A.argmax(1)] * A.max(1))
    if text_scale is not None:
        at = at * text_scale
    at = at[:, None] * 0.55
    af = (rel_f[B.argmax(1)] * B.max(1))[:, None] * 0.45
    tot = at + af
    tot[tot == 0] = 1.0
    at, af = at / tot, af / tot
    logp = at * np.log(np.clip(A, EPS, 1)) + af * np.log(np.clip(B, EPS, 1))
    logp -= logp.max(1, keepdims=True)
    e = np.exp(logp)
    return e / e.sum(1, keepdims=True)


def _json(s):
    m = re.search(r"\{.*?\}", s or "", re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


_SEM = asyncio.Semaphore(2)   # Groq free tier rate-limits aggressive fan-out
FAILURES = {"n": 0}


async def ask(client, system, user, max_tokens=80, retries=8):
    """Throttled + retried. A silently-failed call would default to a neutral value
    and quietly bias every design toward the baseline, so failures are counted and
    reported rather than swallowed."""
    async with _SEM:
        for attempt in range(retries):
            try:
                r = await client.chat.completions.create(
                    model=MODEL, max_tokens=max_tokens, temperature=0.0,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}])
                return _json(r.choices[0].message.content)
            except Exception as e:
                if "RateLimit" in type(e).__name__ and attempt < retries - 1:
                    await asyncio.sleep(4.0 * (attempt + 1))
                    continue
                if attempt == retries - 1:
                    FAILURES["n"] += 1
                    print(f"  ! gave up after {retries}: {type(e).__name__}")
                    return {}
                await asyncio.sleep(1.0)
    return {}


SYS_BINARY = (
    "Two emotion detectors disagree about a personal journal entry. You decide which "
    "to believe.\n"
    "IMPORTANT PRIOR: when these two disagree, the FACE detector is historically "
    "correct about 71% of the time and the TEXT detector only about 17% of the time. "
    "So prefer the face detector UNLESS the wording gives clear, specific evidence "
    "for the text detector's reading (an explicitly named feeling, an unambiguous "
    "description of the situation).\n"
    'Reply ONLY as JSON: {"choice": "text" or "face", "confidence": 0-100}'
)

SYS_TRUST = (
    "You judge how literally a personal journal entry means its emotional wording. "
    "You do NOT name the emotion.\n"
    "Score 0-100:\n"
    "  100 = states a feeling plainly and means it literally\n"
    "   50 = little emotional content, vague, or mixed signals\n"
    "    0 = sarcastic, ironic, heavily negated, or the words contradict the real feeling\n"
    'Reply ONLY as JSON: {"trust": 0-100, "sarcasm": true/false, "vague": true/false}'
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paired-set", default="paired_set_journal.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv(os.path.join(_HERE, "..", ".env"))
    from groq import AsyncGroq

    data = json.load(open(os.path.join(_HERE, "results", args.paired_set)))
    print(f"paired set: {args.paired_set}")

    cal = [p for p in data["pairs"] if p["split"] == "calib"]
    tst = [p for p in data["pairs"] if p["split"] == "test"]
    Tc = np.stack([vec(p["text_dist"]) for p in cal])
    Fc = np.stack([vec(p["face_dist"]) for p in cal])
    yc = np.array([IDX[p["true"]] for p in cal])
    T_text, T_face = fitT(Tc, yc), fitT(Fc, yc)
    rel_t = class_reliability(ts(Tc, T_text), yc)
    rel_f = class_reliability(ts(Fc, T_face), yc)

    fusion = FusionLayer()
    sub = []
    for p in tst:
        tr = {"dominant_emotion": p["text_pred"], "confidence": max(p["text_dist"].values()),
              "all_scores": p["text_dist"]}
        fr = {"emotion": p["face_pred"], "confidence": max(p["face_dist"].values()),
              "all_scores": p["face_dist"]}
        if fusion.fuse(tr, fr).get("resolution_reason", "").startswith("conflict_resolved_to_"):
            sub.append(p)
    print(f"conflict cases: {len(sub)} of {len(tst)} test pairs\n")

    y = np.array([IDX[p["true"]] for p in sub])
    T = np.stack([vec(p["text_dist"]) for p in sub])
    F = np.stack([vec(p["face_dist"]) for p in sub])
    Tcal, Fcal = ts(T, T_text), ts(F, T_face)
    t_pred = np.array([IDX[p["text_pred"]] for p in sub])
    f_pred = np.array([IDX[p["face_pred"]] for p in sub])

    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    async def run_all():
        print("querying LLM (binary choice)...")
        bin_res = await asyncio.gather(*[
            ask(client, SYS_BINARY,
                f'Entry: "{p["text"][:600]}"\n'
                f'TEXT detector says: {p["text_pred"]}\n'
                f'FACE detector says: {p["face_pred"]}')
            for p in sub])
        print("querying LLM (trust score)...")
        trust_res = await asyncio.gather(*[
            ask(client, SYS_TRUST, f'Entry: "{p["text"][:600]}"') for p in sub])
        return bin_res, trust_res

    bin_res, trust_res = asyncio.run(run_all())
    n_bad = sum(1 for r in bin_res if not r) + sum(1 for r in trust_res if not r)
    print(f"failed LLM calls: {n_bad} of {2*len(sub)}"
          + ("  (results below are unreliable)" if n_bad else "  — clean run"))

    choice = np.array([1 if (r.get("choice") == "text") else 0 for r in bin_res])
    conf = np.array([float(r.get("confidence", 0) or 0) for r in bin_res])
    trust = np.array([np.clip(float(r.get("trust", 50) or 50), 0, 100) / 100.0
                      for r in trust_res])

    rows = []

    def rep(name, pred):
        acc = float((pred == y).mean())
        rows.append({"design": name, "accuracy": acc})
        print(f"{name:<46}{acc*100:>8.2f}")
        return acc

    print(f"\n{'DESIGN':<46}{'ACC %':>8}")
    print("-" * 54)
    rep("baseline: always face", f_pred)
    v2_pred = fuse_v2(Tcal, Fcal, rel_t, rel_f).argmax(1)
    rep("baseline: v2 fusion (no LLM)", v2_pred)

    arb_file = ("arbiter_paired_journal.json" if "journal" in args.paired_set
                else "arbiter_paired.json")
    ap_path = os.path.join(_HERE, "results", arb_file)
    if os.path.exists(ap_path):
        prev = json.load(open(ap_path))["accuracy"].get("LLM arbitration (proposed)")
        if prev is not None:
            rows.append({"design": "A: deployed arbiter (7-way classify)", "accuracy": float(prev)})
            print(f"{'A: deployed arbiter (7-way classify)':<46}{prev*100:>8.2f}")

    rep("B: informed binary choice", np.where(choice == 1, t_pred, f_pred))
    for thr in (60, 80):
        override = (choice == 1) & (conf >= thr)
        rep(f"C: abstaining binary (override only if conf>={thr})",
            np.where(override, t_pred, v2_pred))
    rep("D: LLM trust score -> v2 text weight",
        fuse_v2(Tcal, Fcal, rel_t, rel_f, text_scale=trust).argmax(1))
    # sharper variant: trust^2 punishes low-trust text harder
    rep("D2: trust^2 -> v2 text weight",
        fuse_v2(Tcal, Fcal, rel_t, rel_f, text_scale=trust ** 2).argmax(1))

    oracle = float(((t_pred == y) | (f_pred == y)).mean())
    print(f"{'ORACLE (perfect chooser)':<46}{oracle*100:>8.2f}")

    # is the LLM trust score actually informative?
    t_ok = (t_pred == y)
    print(f"\ndiagnostic — mean LLM trust when text is RIGHT = {trust[t_ok].mean():.3f}")
    print(f"                              when text is WRONG = {trust[~t_ok].mean():.3f}")
    print(f"  (a useful signal needs the first to be clearly higher)")
    print(f"binary design picked text on {int(choice.sum())}/{len(sub)} cases; "
          f"text was actually right on {int(t_ok.sum())}")

    out = args.out or f"arbiter_v2_{'journal' if 'journal' in args.paired_set else 'goemotions'}.json"
    with open(os.path.join(_HERE, "results", out), "w") as f:
        json.dump({"paired_set": args.paired_set, "n_conflicts": len(sub),
                   "oracle": oracle, "designs": rows,
                   "trust_when_text_right": float(trust[t_ok].mean()) if t_ok.any() else None,
                   "trust_when_text_wrong": float(trust[~t_ok].mean()) if (~t_ok).any() else None},
                  f, indent=2)
    print(f"\nSaved -> research/results/{out}")


if __name__ == "__main__":
    main()
