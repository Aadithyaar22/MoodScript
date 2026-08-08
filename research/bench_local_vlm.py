"""Benchmark a small local vision-language model on FER2013 faces.

Purpose: measure seconds-per-image and whether the model produces parseable
emotion labels at all, BEFORE committing to the full 252-inference arbitration
run. Downloads ~1GB on first use and runs entirely on CPU. No API, no quota.

Run:  venv/bin/python3 -u research/bench_local_vlm.py --n 5
"""
import argparse
import time

import torch
from datasets import load_dataset
from transformers import AutoModelForImageTextToText, AutoProcessor

MODEL = "HuggingFaceTB/SmolVLM-500M-Instruct"
UNIFIED = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
FER2013_LABELS = UNIFIED  # same order, already label-order-corrected in this repo


def parse(txt):
    t = (txt or "").lower()
    hits = [e for e in UNIFIED if e in t]
    return hits[0] if hits else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--stratified", action="store_true",
                    help="sample n images per CLASS at random instead of the first n")
    args = ap.parse_args()

    print(f"[1/4] downloading + loading {MODEL} (~1GB on first run)...", flush=True)
    t0 = time.time()
    proc = AutoProcessor.from_pretrained(MODEL)
    model = AutoModelForImageTextToText.from_pretrained(MODEL, dtype=torch.float32).eval()
    print(f"      loaded in {time.time()-t0:.0f}s", flush=True)

    print("[2/4] loading FER2013 test split...", flush=True)
    ds = load_dataset("clip-benchmark/wds_fer2013", split="test")
    print(f"      {len(ds)} images", flush=True)

    if args.stratified:
        import random
        random.seed(0)
        by = {}
        for i, c in enumerate(ds["cls"]):
            by.setdefault(FER2013_LABELS[c], []).append(i)
        idxs = [i for e in UNIFIED for i in random.sample(by[e], min(args.n, len(by[e])))]
        print(f"      stratified: {args.n}/class -> {len(idxs)} images", flush=True)
    else:
        idxs = list(range(args.n))

    print(f"[3/4] running {len(idxs)} inferences...", flush=True)
    opts = ", ".join(UNIFIED)
    times, correct, parsed = [], 0, 0
    per_class = {}
    for i in idxs:
        ex = ds[i]
        img = ex["jpg"].convert("RGB").resize((384, 384))
        truth = FER2013_LABELS[ex["cls"]]
        msgs = [{"role": "user", "content": [
            {"type": "image"},
            {"type": "text",
             "text": f"What emotion is this person's face showing? "
                     f"Answer with exactly one word from: {opts}"}]}]
        prompt = proc.apply_chat_template(msgs, add_generation_prompt=True)
        inputs = proc(text=prompt, images=[img], return_tensors="pt")
        t = time.time()
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=12, do_sample=False)
        dt = time.time() - t
        txt = proc.batch_decode(out[:, inputs["input_ids"].shape[1]:],
                                skip_special_tokens=True)[0].strip()
        got = parse(txt)
        parsed += got is not None
        correct += got == truth
        times.append(dt)
        per_class.setdefault(truth, [0, 0])
        per_class[truth][1] += 1
        per_class[truth][0] += (got == truth)
        if not args.stratified:
            print(f"      {dt:5.1f}s  true={truth:<10} got={str(got):<10} raw={txt[:32]!r}", flush=True)

    n = len(idxs)
    avg = sum(times) / len(times)
    print(f"[4/4] mean {avg:.1f}s/image | parsed {parsed}/{n} | correct {correct}/{n} "
          f"= {correct/n*100:.1f}%", flush=True)
    if args.stratified:
        print("      per class:", flush=True)
        for e in UNIFIED:
            if e in per_class:
                c, t = per_class[e]
                print(f"        {e:<11} {c}/{t}", flush=True)
    print(f"      (specialised face model on this benchmark: 88.35%)", flush=True)
    print(f"      full arbitration run = 252 inferences ≈ {avg*252/60:.0f} min", flush=True)


if __name__ == "__main__":
    main()
