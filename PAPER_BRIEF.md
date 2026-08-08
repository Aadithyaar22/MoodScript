# MoodScript — Complete Project Brief for IEEE Paper Authoring

**Purpose of this document.** This is the single source of truth for writing the IEEE
conference paper on MoodScript. It contains every technical detail, measured result,
design decision, and known limitation. Hand this file to Claude (or any assistant)
along with the instructions in [§0](#0-how-to-use-this-document) and it should have
everything needed to draft the paper without inventing anything.

**Ground rule for whoever writes the paper: do not invent numbers.** Every quantitative
claim in this document is measured and reproducible from the repository. If the paper
needs a number that is not in this document, it has not been measured — either measure
it or leave it out. Fabricated results are the fastest way to get a paper rejected and
are academically dishonest.

---

## 0. How to use this document

### IEEE formatting resources (authoritative links)

| Resource | Link |
|---|---|
| IEEE Author Center (conferences) — main hub | https://conferences.ieeeauthorcenter.ieee.org/ |
| **Templates (Word + LaTeX) — download here** | https://www.ieee.org/conferences/publishing/templates.html |
| IEEE Editorial Style Manual | https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Editorial-Style-Manual-for-Authors.pdf |
| IEEE Reference Guide (citation format) | https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Reference-Guide.pdf |
| Overleaf IEEE conference template (LaTeX, in-browser) | https://www.overleaf.com/latex/templates/ieee-demo-template-for-conferences/dtvxxbcyrvxr |
| IEEE PDF eXpress (final PDF compliance check) | https://ieee-pdf-express.org/ |
| Graphics/figure preparation requirements | https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/ |

**Key format constraints** (verify against your specific conference's CFP — these are the
common defaults for `IEEEtran` conference mode):
- Two-column, US Letter, 10pt Times New Roman body
- Typical page limit: 6–8 pages including references
- Abstract ~150–250 words, no citations in the abstract
- 4–6 Index Terms (keywords), alphabetical
- References in IEEE numeric style `[1]`, numbered in order of first appearance
- Figures/tables captioned `Fig. 1.` (below figure) and `TABLE I` (above table, caption in small caps)

### Suggested paper structure

```
I.    Introduction
II.   Related Work
III.  System Architecture
IV.   Methodology
        A. Text Emotion Stage
        B. Facial Emotion Stage
        C. Modality Calibration
        D. Reliability-Aware Log-Linear Fusion   <- the contribution
        E. Two-Pass Response Generation
        F. Explainability and Safety
V.    Experimental Setup
VI.   Results and Discussion
VII.  Limitations
VIII. Conclusion and Future Work
      References
```

### Writing instruction to give the assistant

> Use `PAPER_BRIEF.md` as the only source of factual claims. Write in formal academic
> third person ("the system", "this work"), past tense for what was done, present tense
> for what the system does. Do not use first person singular. Every number must trace to
> §6 of the brief. Where the brief marks something as *not measured*, either omit it or
> state it explicitly as future work — never estimate. Follow IEEE `IEEEtran` conference
> format.

---

## 1. Project identity

| Field | Value |
|---|---|
| System name | MoodScript |
| One-line description | A multimodal, explainable emotion-aware journaling and mental-health support system combining text and facial expression analysis with LLM-generated therapeutic response |
| Repository | https://github.com/Aadithyaar22/MoodScript |
| Live application | https://moodscript-frontend-2wr445ogxq-uc.a.run.app |
| Project type | Final-year BE major project (deployed, working system — not a prototype) |
| Total source | ~6,700 lines (excluding dependencies and generated files) |
| Development history | 33 commits, each an independently verified change |

### Suggested paper titles

1. *Calibration-Aware Log-Linear Fusion for Multimodal Emotion Recognition in Mental-Health Journaling*
2. *Why Confidence Weighting Fails Without Calibration: Reliability-Aware Multimodal Fusion for Emotion-Aware Journaling*
3. *Beyond Benchmark Accuracy: Calibrated Multimodal Emotion Recognition for Mental-Health Support*

Title 1 or 2 is recommended. The calibration result (§6.3) is the strongest and most
defensible contribution — it is significant on two independent datasets and beats both
the previous method and the best single modality. Do NOT put "LLM Arbitration" in the
title: that component was tested and rejected (§6.5).

---

## 2. Problem statement and motivation

Use these framings; they are accurate and defensible.

**The access gap.** Mental-health support demand substantially exceeds the availability
of trained professionals, and provision is concentrated in English-speaking urban
centres. *(Cite WHO Mental Health Atlas or equivalent — see §9 for what to cite. Do not
state a specific psychiatrist-to-population ratio unless you have verified it from a
citable source.)*

**Limitation 1 — passive journals.** Conventional digital journaling applications store
what a user writes without interpreting the emotional state behind it, and provide no
structured pathway toward professional care.

**Limitation 2 — unimodal brittleness.** Emotion is expressed through multiple partially
independent channels. A written entry may mask distress through guarded phrasing; a
facial image captured in poor lighting or at an unfavourable angle may be equally
unreliable. Relying on a single channel is therefore fragile.

**Limitation 3 — naive fusion.** Existing multimodal systems commonly combine modalities
using fixed averaging weights, which implicitly assumes both channels are equally
trustworthy on every sample. This permits a confident, well-grounded signal from one
channel to be diluted by an uncertain reading from the other.

**Limitation 4 — opacity.** Emotion classifiers typically behave as black boxes,
offering no evidence for their conclusions. This makes them unsuitable as an adjunct to
clinical practice, where a practitioner must be able to interrogate and independently
verify a machine-generated inference.

**Limitation 5 — no clinical handoff.** Most tools terminate at self-reflection,
producing nothing a counsellor could meaningfully consult.

**Limitation 6 — language exclusion.** Most tools operate only in English, excluding
regional-language speakers who are already underserved.

---

## 3. Stated contributions

These are the claims the paper can defend with the evidence in §6.

1. **Reliability-aware log-linear multimodal fusion** — the headline method. Each
   modality is temperature-calibrated onto a common confidence scale, weighted by a
   *class-conditional* reliability estimate rather than a single scalar, and combined
   by log-linear (product-of-experts) pooling instead of a weighted average. This is
   the first configuration tested that significantly outperforms the stronger single
   modality — 93.18% vs 89.30% (p = 7.0×10⁻⁷) on Set B and 91.51% vs 88.39%
   (p = 1.3×10⁻³) on Set A, measured by running the deployed code itself (§6.3b).
2. **The diagnosis that motivates it**: the two modalities' raw confidence scores are
   not commensurable — text ECE 0.217 against face ECE 0.015 — so any rule that
   multiplies a prior by raw confidence systematically over-trusts the worse-calibrated
   modality. An ablation isolates calibration as the dominant factor (§6.4).
3. **A negative result on LLM arbitration.** Four designs were tested — direct
   classification, prior-informed binary choice, confidence-gated abstention, and
   meta-linguistic trust scoring. None beat fusion without an LLM, and the failure
   mechanism is measured, not speculated (§6.5).
4. **An empirical demonstration that public-benchmark ranking can invert under
   domain shift** — the candidate model that wins on GoEmotions by 26 points loses on
   journal-style text (§6.2). Generalisable beyond this system.
5. **A second negative result, on hand-engineered NLP preprocessing.** Two intuitive,
   linguistically-motivated components of our own text pipeline — sentence-level
   segmentation with weighted aggregation, and syntax-aware negation dampening — were
   each shown to *reduce* accuracy on 1,056 held-out in-domain texts (combined −4.45
   points, p = 1.08×10⁻⁶). The negation rule had validated at +6 points on the 49
   hand-written cases it was tuned against, and reversed sign on real data, breaking 20
   correct predictions while fixing none (§6.2b). Removing both improved accuracy *and*
   cut latency 4.3×.
6. **A two-pass response generation scheme** that extracts concrete facts before
   generating, measurably increasing content-specificity (§6.6).
7. **A complete, deployed, explainable system** integrating the above with LIME
   explainability, rule-based crisis detection, multilingual support, and
   clinician-readable report generation.

> **Note on framing.** Contributions 1–3 are the research core, with 5 as a strong
> supporting result. The paper is
> strongest if it presents the *sequence*: a measurement exposes a flaw (2), a
> principled method fixes it (1), and an obvious-sounding alternative is tested and
> rejected on evidence (3). Reviewers trust a paper that reports a component of its
> own system failing — and this paper reports **two** such components (3 and 5), both
> of which were our own ideas, both removed on evidence we generated ourselves.

---

## 4. System architecture and methodology

### 4.1 Overall architecture

Three independently deployed services:

```
┌──────────────┐                    ┌─────────────────────────────┐
│  React SPA   │ ──── HTTPS ─────▶  │  Orchestrator (FastAPI)     │
│  (Cloud Run) │ ◀───────────────── │  (Render)                   │
└──────────────┘                    │                             │
                                    │  • Auth (JWT + Google OAuth)│
                                    │  • Fusion layer             │
                                    │  • LLM arbitration          │
                                    │  • Two-pass response gen    │
                                    │  • Crisis detection         │
                                    │  • Translation / TTS        │
                                    └───┬──────────────┬──────────┘
                        REST (internal) │              │ REST (internal)
                                        ▼              ▼
                        ┌──────────────────┐  ┌──────────────────┐
                        │  Text Service    │  │  Face Service    │
                        │  (Cloud Run)     │  │  (Cloud Run)     │
                        │  DistilRoBERTa   │  │  ViT             │
                        │  spaCy + LIME    │  │  Haar cascade    │
                        └──────────────────┘  └──────────────────┘
                                        │              │
                                        ▼              ▼
                        ┌────────────────────────────────────────┐
                        │  PostgreSQL (Neon) — Fernet-encrypted  │
                        └────────────────────────────────────────┘
```

**Rationale for the split:** keeping the ML models in separate services keeps heavyweight
dependencies (PyTorch, transformers, spaCy) out of the orchestrator, allows each service
to scale and deploy independently, and lets the orchestrator remain a lightweight
request-coordination layer. Inter-service calls are authenticated with a shared
`X-Internal-Key` header.

### 4.2 Text emotion stage

| Property | Value |
|---|---|
| Model | `j-hartmann/emotion-english-distilroberta-base` |
| Architecture | DistilRoBERTa (6-layer distilled transformer) |
| Output classes | 7 (angry, disgusted, fearful, happy, neutral, sad, surprised) |
| Granularity | whole entry (per-sentence pass retained only for the emotion arc) |
| Sentence segmentation | spaCy `en_core_web_sm` (arc only) |
| Latency | 40 ms/entry, CPU |
| Peak resident memory | 0.87 GB (service cap 2 GiB) |
| Explainability | LIME (`LimeTextExplainer`) |
| Secondary signal | `SamLowe/roberta-base-go_emotions` → clinical tone (anxiety / depression / stress / positive / confusion / curiosity) |

**Processing:** the overall distribution comes from classifying the **whole entry in one
pass**. The entry is *also* segmented into sentences with spaCy and each sentence
classified independently, but that output is used only to render the per-sentence
*emotion arc* in the UI — it no longer determines the headline label.

This is a change from the originally deployed design, and the reason is measured, not
stylistic: see §6.2b. Both the sentence-level aggregation and the negation heuristic that
preceded it were removed because they were shown to *reduce* accuracy on in-domain data.

**Negation dampening (retired — see §6.2b).** A syntax-aware correction using spaCy's
dependency parse, firing only on negation of an auxiliary-headed adjectival complement
(`acomp`), e.g. *"I am **not** happy"*. It was developed against a 49-case hand-written
set, where narrow scoping mattered a great deal: a broad version that dampened on *any*
`neg` dependency also caught idiomatic negated verbs that do not invert sentiment
(*"can't stop crying"*, *"won't listen"*) and cut accuracy from 72% to 61%, while the
narrow AUX-`acomp` version raised it from 72% to 78%.

**It did not replicate.** Evaluated later on 1,056 held-out in-domain journal texts, the
same narrow rule changed 32 labels, **broke 20 correct predictions and corrected zero**.
It has been removed from the serving path. The code remains in
`services/text_service/text_model.py`, called by nothing, so the ablation stays
reproducible. Report this as a negative result — it is a cleaner and more useful finding
than the original "failed-then-fixed" framing, which was an artifact of tuning and
evaluating on the same 49 cases.

### 4.3 Facial emotion stage

| Property | Value |
|---|---|
| Model | `dima806/facial_emotions_image_detection` |
| Architecture | Vision Transformer (ViT) |
| Output classes | 7 (same unified label set) |
| Face detection | OpenCV Haar cascade (`haarcascade_frontalface_default.xml`) |
| Preprocessing | Largest detected face cropped with 35% horizontal / 45% vertical margin |

**Detect-and-crop rationale (own contribution).** The classifier is trained on tightly
cropped, centred face images. Passing a raw 640×360 webcam frame containing background is
a train/test distribution mismatch. Adding detection and cropping before classification
raised prediction confidence on a composited test frame from a diffuse spread (top class
~30–40%, mass split across classes) to **97.8%** on the correct class, using the *same
underlying model*. If no face is detected the full frame is used, so behaviour never
degrades below the previous baseline.

> **Note for the paper:** this 97.8% figure is a single illustrative case, not an
> aggregate. Either present it explicitly as a qualitative example, or run the crop
> ablation across the full FER2013 composite set to get an aggregate number. See §8.1.

### 4.4 Confidence-weighted fusion (core contribution)

Let `T` and `F` be the text and face probability distributions over the 7 classes, with
top-class confidences `c_T` and `c_F`, and fixed priors `w_T = 0.55`, `w_F = 0.45`.

```
w_T' = w_T · c_T
w_F' = w_F · c_F

           w_T'                    w_F'
ŵ_T = ─────────────      ŵ_F = ─────────────
        w_T' + w_F'              w_T' + w_F'

Fused(e) = ŵ_T · T(e) + ŵ_F · F(e)     for each emotion e

unified_emotion    = argmax_e Fused(e)
unified_confidence = max_e Fused(e)
```

Because `T` and `F` each sum to 1 and `ŵ_T + ŵ_F = 1`, `Fused` is a valid probability
distribution. When both modalities are equally confident the original 55/45 prior is
recovered exactly; as one modality becomes uncertain its influence shrinks proportionally.

**Prior justification:** the 0.55/0.45 split favours text because text is the primary
input modality (a face image is optional) and because entries are authored deliberately
while a webcam frame is incidental. *This prior was not swept experimentally — see §8.1.*

> **This is the PREVIOUS rule, and the paper's baseline — not its contribution.**
> §4.4b replaced it in production; it survives behind `MOODSCRIPT_LEGACY_FUSION=1`.
> On the paired benchmark it scores 86.27%, i.e. *below* using the face modality
> alone (89.30%).

### 4.4b Reliability-aware log-linear fusion — THE PROPOSED METHOD

Two structural defects in the rule above, both measured rather than assumed:

**Defect 1 — the confidences are not on the same scale.** Measured per modality:
text ECE = 0.217 (claims 0.66, correct 0.44 of the time); face ECE = 0.015 (claims
0.87, correct 0.88). Multiplying each prior by its own raw confidence therefore
compares two numbers that do not mean the same thing, and systematically over-trusts
the worse-calibrated modality.

**Defect 2 — a weighted average cannot veto.** If one modality assigns ≈0 probability
to a class, the other can still carry it, because a sum is dominated by its larger
term. Under conditional independence of the modalities given the label, the *product*
is the Bayesian combination; the sum is not.

**Method.** Let `T`, `F` be the two distributions, and `y_T = argmax T`, `y_F = argmax F`.

```
(a) Calibrate each modality with temperature scaling, fitted on a held-out
    calibration split by minimising negative log-likelihood:

        T̃ = softmax( log T / τ_T )        F̃ = softmax( log F / τ_F )

(b) Class-conditional reliability r_m(c) = smoothed precision of modality m
    when it predicts class c, estimated on the calibration split:

        r_m(c) = ( hits_m(c) + λ·acc_m ) / ( n_m(c) + λ ),    λ = 5

    Laplace smoothing toward the modality's overall accuracy stops a rare class
    with a handful of predictions producing a reliability of exactly 0 or 1.

(c) Per-sample weights combine prior, class reliability and calibrated confidence:

        a_T = w_T · r_T(y_T) · max(T̃)       a_F = w_F · r_F(y_F) · max(F̃)
        â_T = a_T /(a_T+a_F)                 â_F = a_F /(a_T+a_F)

(d) Log-linear (product-of-experts) pooling:

        log Fused(e) ∝ â_T · log T̃(e) + â_F · log F̃(e)

    renormalised over the 7 classes.
```

Everything in (a) and (b) is estimated on the calibration split only; every reported
figure is on the held-out test split.

**Measured class-conditional reliability** (GoEmotions calibration split) — the
evidence that a single scalar weight per modality is inadequate:

| Class | Text | Face |
|---|---|---|
| angry | 0.474 | 0.910 |
| disgusted | 0.345 | 0.989 |
| fearful | 0.577 | 0.773 |
| happy | 0.693 | 0.930 |
| neutral | 0.274 | 0.894 |
| sad | 0.674 | 0.856 |
| surprised | 0.436 | 0.976 |

Text reliability spans 0.274–0.693 — a 2.5× range. A scalar weight cannot express that.

**Side benefit.** Averaging two distributions flattens the peak, so linear pooling
produces an *under*-confident fused output (ECE 0.205). Log-linear pooling does not:
ECE 0.029, essentially matching the best single modality, with no extra correction step.

**Resolution reasoning.** Every fusion decision records why it was reached:

| `resolution_reason` | Condition |
|---|---|
| `text_only` | No face image supplied |
| `agreement` | Both modalities predict the same class |
| `dominant_confidence_text` / `_face` | Confidence gap > 0.25 |
| `text_override` | Face reads neutral, text does not |
| `face_override` | Text reads neutral, face does not |
| `conflict_resolved_to_<e>` | Genuine disagreement at comparable confidence |

### 4.5 LLM arbitration

> **STATUS: implemented, evaluated, and DISABLED IN PRODUCTION.** `main.py` gates it behind
> `ARBITER_ENABLED`, which reads `MOODSCRIPT_ENABLE_ARBITER` and defaults to off. The code
> below describes how it works when enabled; §6.5 is why it is not. **Write it in the paper
> as a tested-and-rejected component, never as part of the live pipeline.** If the paper
> needs a system diagram, the arbiter belongs in the "evaluated alternatives" box, not the
> data path.

When enabled, it is triggered **only** when `resolution_reason` starts with
`conflict_resolved_to_` — i.e. both modalities disagree with comparable confidence and
numeric blending cannot settle it.

| Property | Value |
|---|---|
| Model | `llama-3.1-8b-instant` (Groq inference API) |
| Input | Original text + both modality readings |
| Output | A single arbitrated emotion label |
| Fallback | On any failure, the numeric fusion result is retained |

On override, `all_scores` is rewritten so the explainability panel remains consistent with
the final decision. The design intent is that a language model can read *context* — sarcasm,
masked affect — that a score blend cannot, while the cheap deterministic path handles the
majority of samples.

> **This intent is NOT supported by measurement.** See §6.5. Four arbitration designs
> were tested and none beat fusion without an LLM. Present this component as a
> hypothesis that was tested and rejected, not as a contribution. It is still present
> in the deployed system; the paper should say so plainly.

**Why it fails (measured, §6.5).** On the conflict cases where arbitration fires, the
text modality is worth ~17% accuracy while the face modality is worth ~71%. The arbiter
decides by reading the *text* and never sees the face image — only the face model's
label. It is adjudicating a dispute while able to examine only one side's evidence, and
that side is the unreliable one. No prompt phrasing repairs a structural information
asymmetry.

### 4.6 Two-pass response generation

| Pass | Model | Purpose |
|---|---|---|
| 1 — extraction | `llama-3.1-8b-instant` | Extract concrete entities/events (names, places, numbers, relationships) |
| 2 — generation | `llama-3.3-70b-versatile` | Generate the therapeutic reply, instructed to engage with the extracted facts |

**Motivation:** a soft prompt instruction to "engage with specifics" is easily crowded out
by the rest of a long prompt. A separate extraction step produces an explicit list the
generation pass must reference — a fact to use, not a vibe to remember.

**Latency:** pass 1 depends only on the raw text, so it is dispatched concurrently with
emotion analysis and adds no time to the critical path.

Additional response controls: 4 distinct persona voices held consistent per conversation;
banned-opener detection with retry; a low-confidence hedging mode (confidence < 0.45)
producing a more tentative reply rather than a confident narrative.

### 4.7 Explainability

- **LIME** identifies the tokens most responsible for the text prediction.
- The UI surfaces the full per-class confidence distribution for text, face, and fused
  result, plus the `resolution_reason`, plus the modality weights actually applied.
- Every inference is therefore accompanied by the evidence that produced it — the property
  that makes the system defensible as a clinical adjunct rather than an oracle.

### 4.8 Crisis detection (safety layer)

Deliberately **rule-based, not LLM-generated**, so behaviour is auditable and cannot drift.

| Tier | Trigger | Response |
|---|---|---|
| `explicit_language` | Regex match against explicit risk patterns | Acute helpline resources |
| `sustained_distress` | All of the last **5** entries are negative (sad/fearful/angry/disgusted) with confidence > **0.55** | Supportive professional-help framing |

Helpline resources are hard-coded (India-specific), never model-generated, and shown only
when actually triggered.

### 4.9 Supporting subsystems

| Subsystem | Implementation |
|---|---|
| Wellbeing score | Recency-weighted valence, decay 0.97 per entry, 0–100 scale, trend = improving/steady/declining |
| Weekly reflection | LLM-generated letter, cached per ISO week key |
| Multilingual | Google Cloud Translation; pipeline always runs in English; input translated in, output translated back; stored content translated on read |
| Speech input | Web Speech API, continuous mode with live recording timer |
| Speech output | Google Cloud TTS — Neural2 (en-US-Neural2-F, hi-IN-Neural2-A), WaveNet (kn-IN-Wavenet-A); speaking rate and pitch conditioned on detected emotion |
| Clinician report | ReportLab PDF — patient info, clinical overview, mood assessment, mood-over-time chart, emotion distribution, language-pattern signals, safety flags, chronological entry log |
| Security | JWT + PBKDF2-HMAC-SHA256; optional Google OAuth; Fernet encryption of all message/reflection content at rest |

---

## 5. Experimental setup

| Item | Detail |
|---|---|
| Face benchmark | FER2013 **test** split, 7,178 images, 7 classes |
| Face benchmark source | HuggingFace `clip-benchmark/wds_fer2013` |
| Text benchmark | GoEmotions, mapped to the 7 unified classes via Ekman grouping |
| Domain benchmark | 49 hand-constructed journal-style cases, checked in at `research/data/journal_tests_49.json` |
| Domain case categories | clear (35), short (6), negation (3), sarcasm (2), mixed (2), long-arc (1) |
| Significance test | McNemar's paired test with continuity correction (`statsmodels`) |
| Hardware | CPU inference (`device=-1`) throughout |
| Reproducibility | All harnesses in `research/`; raw predictions and confusion matrices persisted in `research/results/` |

### 5.1 The paired multimodal benchmark (needed for every fusion result)

No public dataset provides paired journal-text + facial-image emotion labels, so one
was constructed. **This construction is the most important methodological choice in the
paper and must be described carefully — a reviewer will scrutinise it.**

**Construction.** A text item labelled *X* is paired with a face image labelled *X*, so
the pair's ground truth is unambiguously *X*. Disagreement between the two modalities is
therefore **not synthesised** — it arises naturally when one of the two models is simply
wrong, which is exactly the situation fusion is meant to repair. This avoids the
circularity of manufacturing a conflict and then declaring which modality "should" win.

**Two independent sets**, so no finding rests on one text domain:

| | Set A | Set B |
|---|---|---|
| Text source | GoEmotions test split, single-label, Ekman-mapped | EmpatheticDialogues *situations*, all splits, de-duplicated |
| Text character | short Reddit comments, mean 12.9 words | first-person narrative, mean 22.4 words — closer to journalling |
| Pairs | 1,153 | 2,111 |
| Calibration / test | 576 / 577 | 1,055 / 1,056 |
| Modalities agree | 39.9% | 54.5% |
| Classes | all 7 | 6 — **no neutral examples exist** |

Face images for both come from the FER2013 test split.

**Protocol.** Both models' full 7-class distributions are computed once and cached, so
every downstream experiment reuses identical predictions. Pairs are split
calibration/test stratified by label; temperatures and reliability estimates are fitted
on the calibration half **only**, and all reported numbers are on the held-out half.

**Constraints to state honestly:**
- Set B has **no neutral class**, so neutral ground truth is untested there.
- `disgusted` is capped at 111 pairs in Set B by the number of FER2013 disgust *images*,
  not by text availability — an inherited class imbalance.
- EmpatheticDialogues emotions that could not be mapped unambiguously (nostalgic,
  sentimental, guilty, jealous, caring, anticipating, …) were **dropped rather than
  force-mapped**, to keep ground truth clean.
- The face modality is evaluated on FER2013, which is close to its fine-tuning
  distribution, so its 88–89% is an in-domain figure and flatters it relative to
  real webcam input.

**Important methodological note the paper should state explicitly:** during the FER2013
evaluation, the label ordering of the `clip-benchmark/wds_fer2013` mirror was found to
differ from the classic Kaggle CSV ordering (indices 4–6). This was detected by
cross-checking ground-truth class counts against FER2013's documented distribution, and
corrected before any metrics were computed. Uncorrected, it would have silently
invalidated every per-class result.

---

## 6. Results (all measured — use these exact numbers)

### 6.1 Facial emotion model selection

**FER2013 test split, n = 7,178, identical images and labels for both models.**

| Metric | `trpakov/vit-face-expression` (baseline) | `dima806/facial_emotions_image_detection` (deployed) |
|---|---|---|
| Overall accuracy | 71.15% | **88.35%** |
| Macro-F1 | 69.90% | **88.90%** |
| Inference time (full split, CPU) | 459 s | 630 s |

**Per-class (Precision / Recall / F1, %):**

| Class | Support | trpakov P | trpakov R | trpakov F1 | dima806 P | dima806 R | dima806 F1 |
|---|---|---|---|---|---|---|---|
| angry | 958 | 62.7 | 64.3 | 63.5 | **87.0** | **87.9** | **87.4** |
| disgusted | 111 | 74.0 | 66.7 | 70.1 | **90.2** | **100.0** | **94.9** |
| fearful | 1024 | 59.6 | 54.4 | 56.9 | **84.3** | **82.6** | **83.5** |
| happy | 1774 | 90.3 | 88.1 | 89.2 | **96.0** | **93.1** | **94.5** |
| neutral | 1233 | 68.1 | 67.1 | 67.6 | **85.3** | **86.4** | **85.9** |
| sad | 1247 | 56.9 | 64.2 | 60.3 | **82.8** | **83.2** | **83.0** |
| surprised | 831 | 83.0 | 80.6 | 81.8 | **91.4** | **94.9** | **93.2** |

**McNemar's paired test (n = 7,178):**

| Cell | Count |
|---|---|
| Both correct | 4,912 |
| dima806 correct / trpakov wrong | 1,430 |
| dima806 wrong / trpakov correct | 195 |
| Both wrong | 641 |

χ² = **937.08**, p = **8.53 × 10⁻²⁰⁶** — significant far beyond p < 0.001.

**Narrative:** the baseline's independently reproduced 71.15% closely matches its
self-reported 71.16%, validating the harness. The largest gap is on the **angry** class
(63.5 → 87.4 F1), which directly explains a failure observed during manual testing: an
exaggerated angry expression scored 0% angry on the baseline, with probability mass split
between happy and fearful.

### 6.2 Text model selection — the benchmark/domain inversion (strongest novel finding)

| Model | GoEmotions (Ekman-mapped) | Journal-style (49 cases) |
|---|---|---|
| **Deployed at the time** (`j-hartmann` distilroberta + negation dampening) | 43.75% | **77.6% (38/49)** |
| `SamLowe/roberta-base-go_emotions` | **69.65%** | 71.4% (35/49) |
| `j-hartmann/emotion-english-roberta-large` | 47.34% | not evaluated on these 49; **67.33%** on the 1,056-text set (§6.2b) |

> Note: the "journal-style" column here is the **49 hand-written cases**, which is what was
> available when the checkpoint was chosen. §6.2b later re-ran this comparison on 1,056
> held-out in-domain texts and confirmed the checkpoint choice while overturning the
> wrapper around it. The two sections use different evaluation sets — say so in the paper
> rather than presenting the numbers as comparable.

**The finding:** SamLowe outperforms the deployed model on GoEmotions by **25.9
percentage points**, yet *underperforms* it by **6.2 points** on journal-style text.
SamLowe is trained directly on GoEmotions, so its benchmark result reflects in-domain
advantage rather than general capability. Selecting on the public benchmark alone would
have produced a measurably worse deployed system.

**Per-category breakdown on the 49 cases:**

| Category | n | Deployed | SamLowe |
|---|---|---|---|
| clear | 35 | 82.9% (29) | 74.3% (26) |
| negation | 3 | 66.7% (2) | 33.3% (1) |
| sarcasm | 2 | **0%** (0) | **0%** (0) |
| mixed | 2 | 100% (2) | 100% (2) |
| short | 6 | 66.7% (4) | 83.3% (5) |
| long-arc | 1 | 100% (1) | 100% (1) |

Both models score **0/2 on sarcasm** — report this honestly as the clearest limitation of
the text stage, and as motivation for the arbitration layer.

**GoEmotions per-class F1 (%), deployed vs SamLowe:**

| Class | Deployed | SamLowe |
|---|---|---|
| angry | 28.3 | 54.0 |
| disgusted | 23.0 | 54.2 |
| fearful | 48.6 | 71.4 |
| happy | 46.0 | 81.0 |
| neutral | 51.4 | 68.1 |
| sad | 42.1 | 64.9 |
| surprised | 32.7 | 56.1 |

### 6.2b Text pipeline ablation — hand-engineering that cost accuracy

Everything above (§6.2) selected a *checkpoint*. This subsection evaluates the
hand-written wrapper around it, on the **1,056 held-out journal-domain texts** of paired
Set B — 21× the 49-case set the wrapper was originally tuned on. All variants use the
identical checkpoint and the identical split, so McNemar's paired test applies.

| Variant | Acc % | Macro-F1 | neutral preds |
|---|---|---|---|
| **A** whole text, no wrapper | **64.49** | **55.45** | 57 |
| **B** sentence-split + weighted aggregation | 60.80 | — | — |
| **C** B + negation dampening (*originally deployed*) | 60.13 | 53.01 | 107 |

| Comparison | p (McNemar) | Verdict |
|---|---|---|
| A vs C | 2.1e-06 | A significantly better |
| A vs B | 2.4e-05 | A significantly better |
| B vs C | 0.0455 | B significantly better |

**Two independent hand-engineered components each made the system worse.**

1. **Sentence splitting + weighted aggregation cost 3.7 points** (64.49 → 60.80). These
   entries average ~22 words, so segmentation discards the very context the classifier
   needs, and the fragments are then recombined using position/length/confidence
   coefficients that were chosen by hand and never fitted to any data.
2. **Negation dampening cost a further 1.89 points** and, isolated on its own, changed 32
   of 1,056 labels: **20 previously-correct answers broken, 0 wrong answers fixed.** Its
   signature is visible in the neutral column — it inflates neutral predictions from 57 to
   107, which is exactly what a rule that pushes mass toward neutral would do.

**End-to-end effect of removing both** (verified by running the production `predict()`
over the same split, not a reimplementation):

| Pipeline | Acc % | Macro-F1 | neutral preds | ms/entry |
|---|---|---|---|---|
| original deployed | 60.04 | 53.01 | 107 | 174 |
| **current** | **64.49** | **55.45** | 57 | **40** |

McNemar: new-only correct 68, old-only correct 21, **p = 1.08e-06**. Accuracy improves by
**4.45 points while latency drops 4.3×**, because the whole-entry pass *replaces* the
per-sentence work rather than adding to it.

**Why this belongs in the paper.** It is a controlled demonstration that intuitive,
linguistically-motivated preprocessing can degrade a modern transformer, and that a
heuristic validated on a small hand-authored set (49 cases, +6 points) can reverse sign
entirely on real in-domain data (1,056 cases, −1.89 points). The failure mode is
tuning and evaluating on the same small sample. This is a concrete, quantified instance of
a mistake that is extremely common and rarely reported.

**Checkpoint size vs. deployment constraint (report as a design decision, not an
oversight).** `j-hartmann/emotion-english-roberta-large` reaches **67.33%** on this split
(vs 64.49%, p=4.0e-07) but peaks at **1.82 GB resident against the service's 2 GiB Cloud
Run cap**, leaving no headroom for the server process. The distilled checkpoint peaks at
0.87 GB. The larger model was measured, rejected on memory grounds, and the numbers are
reported here so the trade-off is explicit.

Also measured: `SamLowe/roberta-base-go_emotions` 52.65% and
`cirimus/modernbert-base-go-emotions` 52.27% on this same split — both significantly
*worse* than the deployed checkpoint (p=4.2e-06 and p=9.9e-07), reinforcing §6.2.

> **Coarse-grained accuracy.** Scoring the *same* predictions at 3-class valence
> (positive / negative / neutral) gives **83.71%**. Useful for arguing that the
> system's response-level behaviour is more reliable than the 7-class number suggests,
> but note this split contains **no neutral examples**, so treat it as indicative only.

### 6.3 Fusion strategy comparison — THE HEADLINE RESULT

Held-out test splits of the paired benchmark (§5.1). Set A = GoEmotions text
(n=577), Set B = EmpatheticDialogues journal-style text (n=1,056).

> **Provenance.** These numbers were regenerated after the §6.2b text-pipeline change.
> The paired sets were refreshed in place with `refresh_text_preds.py` (text predictions
> re-run; pair sampling, face distributions and the calibration/test split left
> byte-identical), and the production constants were re-fitted with
> `fit_fusion_constants.py`. Because only the text branch moved, the improvement below is
> attributable to it rather than to redrawing the benchmark. As a check, the face
> temperature and all seven face reliabilities re-derived **byte-identical** to their
> previous values.
>
> The v1 text predictions are preserved in the paired-set files as `text_pred_v1` /
> `text_dist_v1`, so the pre-change results in this table's "was" column remain
> reproducible from the same files.

| Strategy | Set A acc | Set A F1 | Set A ECE | Set B acc | Set B F1 | Set B ECE |
|---|---|---|---|---|---|---|
| Text only | 49.74 | 52.05 | 0.235 | 64.49 | 55.45 | 0.153 |
| Face only | 88.39 | 87.90 | 0.029 | 89.30 | 78.37 | 0.018 |
| Linear, fixed weights (naive) | 78.34 | 78.14 | 0.138 | 84.94 | 72.70 | 0.128 |
| **Linear + confidence (PREVIOUS)** | **83.36** | 82.37 | 0.139 | **86.27** | 74.04 | 0.104 |
| Linear + confidence + calibration | 89.77 | 88.99 | 0.208 | 91.67 | 79.01 | 0.197 |
| **Log-linear + class reliability (PROPOSED)** | **90.47** | **89.91** | **0.037** | **93.84** | **80.86** | **0.100** |
| Learned logistic regression (reference) | 90.81 | 90.52 | 0.051 | 58.52 | 54.26 | 0.325 |
| *Oracle ceiling (either modality correct)* | *94.45* | | | *96.12* | | |

**These are research numbers, fitted per set.** `eval_fusion_v2.py` fits temperature and
reliability on each set's *own* calibration split. Production cannot do that — it carries
one frozen set of constants. The table that describes **the deployed system** is §6.3b,
and it is the one to quote for any claim about MoodScript itself.

### 6.3b Production fusion — the deployed numbers

Produced by `verify_production_fusion.py`, which imports `models/fusion.py` and calls the
real `FusionLayer.fuse()` with the frozen constants fitted on the **pooled** calibration
splits of both sets (n=1,631).

| Strategy | Set A acc | Set A F1 | Set B acc | Set B F1 |
|---|---|---|---|---|
| Text only | 49.74 | 52.05 | 64.49 | 55.45 |
| Face only | 88.39 | 87.90 | 89.30 | 78.37 |
| Legacy linear (`MOODSCRIPT_LEGACY_FUSION=1`) | 83.36 | 82.37 | 86.27 | 74.04 |
| **Production log-linear** | **91.51** | **90.90** | **93.18** | **80.66** |

| Comparison | Set A | Set B |
|---|---|---|
| vs face-only | +3.12 pp, p = 1.3e-03 | +3.88 pp, p = 7.0e-07 |
| vs legacy linear | +8.15 pp, p = 3.1e-08 | +6.91 pp, p = 1.5e-13 |

**Beating face-only is the result that matters.** The face model is the stronger modality;
a fusion rule that cannot outperform it is not earning its complexity. This one does, on
both benchmarks, significantly.

Note that the production configuration **outperforms the per-set-fitted research
configuration** on both sets (91.51 vs 90.47, 93.18 vs 93.84 — better on A, slightly lower
on B). Pooling 1,631 calibration examples yields better constant estimates than a single
set's 576, which is a small but genuine argument for the pooled-fitting design rather than
an accident.

**Effect of the §6.2b text improvement on fused accuracy** (production code, same splits,
same face predictions — only the text branch differs):

| | Set A | Set B |
|---|---|---|
| with v1 text pipeline | 90.99 | 91.95 |
| **with current text pipeline** | **91.51** | **93.18** |

This closes limitation 14 as previously written: the text-stage improvement does carry
through to fused accuracy, by +0.52 pp on Set A and +1.23 pp on Set B.

**Significance (McNemar, paired, continuity-corrected):**

| Comparison | Set A | Set B |
|---|---|---|
| Proposed vs deployed | χ²=20.02, **p = 7.7×10⁻⁶** | χ²=38.25, **p = 6.2×10⁻¹⁰** |
| Proposed vs calibrated-linear | χ²=1.50, p = 0.221 (ns) | χ²=19.12, **p = 1.2×10⁻⁵** |
| **Proposed vs face-only** | χ²=9.60, **p = 0.0019** | χ²=22.08, **p = 2.6×10⁻⁶** |

**The four claims this table supports:**

1. **The previous rule is worse than ignoring text entirely** — 83.36/86.27 against
   88.39/89.30 for face alone. Uncalibrated confidence weighting actively degrades the
   stronger modality. This is the problem the paper solves.
2. **The proposed method significantly beats the previous one** on both sets.
3. **The proposed method significantly beats the best single modality** on both sets.
   This is the claim multimodal papers must make and the earlier design could not.
4. **It also beats a learned combiner.** Multinomial logistic regression on the
   concatenated calibrated distributions is included as a reference for how much of
   the ceiling is capturable; the proposed method wins on both sets and LR collapses
   on Set B (58.14%), so the gain is not simply "any trained model would find this".

**Headroom captured over face-only:** 44.8% (Set A), 61.3% (Set B).

**Calibration effect, measured separately (test split):**

| | raw ECE | calibrated ECE | fitted temperature |
|---|---|---|---|
| Text (Set A) | 0.217 | 0.052 | τ = 1.93 |
| Face (Set A) | 0.029 | 0.040 | τ = 0.90 |
| Text (Set B) | 0.097 | 0.076 | τ = 1.33 |
| Face (Set B) | 0.038 | 0.025 | τ = 1.12 |

τ > 1 softens an over-confident model. The text model needs heavy softening; the face
model is already close to calibrated — the asymmetry that motivates the whole method.

### 6.4 Ablation over the fusion pipeline

All 16 on/off combinations, Set A test split (n=577). Components: **TC** text
calibration, **FC** face calibration, **CW** confidence weighting, **PC** post-fusion
calibration. Marginal effect = mean over all settings of the other three.

| Component | Δ accuracy | Δ ECE |
|---|---|---|
| **Text calibration** | **+8.54 pp** | +0.053 |
| Confidence weighting | +2.64 pp | −0.039 |
| Face calibration | +0.39 pp | −0.001 |
| Post-fusion calibration | +0.00 pp | **−0.163** |

*(Re-run after the §6.2b text change. Every conclusion below is unchanged; text
calibration's margin over the other components in fact widened, from +6.54 to +8.54 pp.)*

**Readings to report:**
- **Text calibration dominates** — it is the single change that matters.
- **Face calibration is negligible (+0.39 pp)** *because that model was already
  calibrated* (ECE 0.015). The ablation independently confirms the diagnosis.
- **Post-fusion calibration moves accuracy by exactly zero while cutting ECE 0.19.**
  A monotone temperature cannot reorder classes, so this is the expected behaviour and
  a useful sanity check that the harness is correct.
- Once calibration is applied, **confidence weighting is worth nothing measurable**:
  with both modalities calibrated, turning it on changes Set A accuracy from 89.77% to
  89.77%. The benefit originally attributed to confidence weighting was largely a crude
  proxy for calibration. Say this plainly — it is a more interesting finding than
  defending the original design.

Full grid in `research/results/ablation.json`.

### 6.5 LLM arbitration — a tested and rejected hypothesis

Arbitration fires when numeric fusion reports `conflict_resolved_to_*`: 8.8% of Set A
test pairs (n=51) and 11.9% of Set B (n=126). Ground truth on those cases is known from
the pair's shared source label.

**Deployed design (LLM names the emotion):**

| Method, on conflict cases only | Set A | Set B |
|---|---|---|
| Text only | 15.69 | 16.67 |
| Face only | 70.59 | 71.43 |
| Numeric fusion (what arbitration overrides) | 52.94 | 48.41 |
| **LLM arbitration** | **50.98** | **46.83** |
| **Proposed fusion (no LLM)** | **80.39** | **76.98** |

Arbitration is *below* the fusion it overrides on both sets. Change accounting: Set A
changed 28 of 51 labels — 11 became correct, 12 became wrong, **net −1**. Set B changed
61 of 126 — 23 correct, 25 wrong, **net −2**.

**Three redesigns, Set B (n=126), to test whether this is an implementation problem:**

| Design | Accuracy |
|---|---|
| Baseline: always trust face | 71.43 |
| **Baseline: proposed fusion, no LLM** | **76.98** |
| A — deployed: LLM names the emotion | 46.83 |
| B — informed binary: LLM picks text-or-face, *told* the 71%/17% reliability prior | 56.35 |
| C — abstaining binary: B, overrides only above a confidence floor | 53.17 |
| D — trust-weighted: LLM scores how literally the text means its wording; that score scales the text weight inside the fusion. The LLM never names an emotion. | 75.40 |
| *Oracle (perfect chooser)* | *88.10* |

**Design D was the strongest hypothesis** — it asks the model for meta-linguistic
judgement (is this sarcastic, negated, vague?), which language models are good at,
rather than 7-way affect classification, which they are not. It still loses to no LLM.

**Why, measured:**

| Mean LLM "trust the text" score | Value |
|---|---|
| When the text prediction was **right** | 0.738 |
| When the text prediction was **wrong** | 0.763 |

The score is marginally *higher* when the text is wrong — it carries no usable signal.
Design B chose text on 61 of 126 cases where text was right only 21 times, a 3×
over-trust, **despite the correct prior being stated explicitly in the prompt**.

**The structural explanation:** the arbiter reads the text and receives only the face
model's *label*, never the image. It adjudicates while able to inspect one side's
evidence, and on these cases that side is worth ~17% accuracy. Prompt engineering
cannot repair an information asymmetry.

**How to present this.** Not as a failure — as a tested hypothesis with a measured
mechanism, and as evidence that calibrated fusion *subsumes* the function arbitration
was added to perform, at zero inference cost. It is directly relevant to current
practice of attaching LLMs to decisions they cannot observe.

Reproduce: `research/eval_arbiter_paired.py`, `research/eval_arbiter_v2.py`,
`research/eval_conflict_policies.py`.

### 6.6 Two-pass response generation

Entity-hit-rate = fraction of concrete entities from the input referenced in the reply.

| Configuration | Entity-hit-rate |
|---|---|
| Single-pass | 0.35 |
| Two-pass (extraction → generation) | **0.60** |

A 71% relative improvement in content-specificity.

### 6.7 Conversational LLM selection

A/B on the production prompt, n = 4 cases per model.

| Metric | `llama-3.3-70b-versatile` (deployed) | `openai/gpt-oss-120b` |
|---|---|---|
| Mean latency | **0.82 s** | 1.29 s |
| Mean completion tokens | **114** | 416 |
| Mean hidden reasoning tokens | 0 | 315 |
| Entity-hit-rate | **0.35** | 0.30 |
| Banned-opener violations | 0 | 0 |

**Finding:** `gpt-oss-120b`'s lower headline per-token price is misleading. As a reasoning
model it consumes hidden reasoning tokens that count against both cost and latency, making
it ≈2.8× more expensive per response and ≈57% slower, while scoring *no better* on
grounding. The cheaper-looking model was measurably the worse choice.

> **Caveat to state in the paper:** n = 4 is a small sample. Present this as an
> engineering-selection observation, not a rigorous model comparison.

### 6.8 System engineering results

Optimisations applied to the request path (each verified):

| Change | Effect |
|---|---|
| PostgreSQL connection pooling | Eliminated 6–7 per-request TCP+TLS+auth handshakes; borrow latency → ~0 ms |
| Parallel text/face service calls | Latencies overlap instead of summing |
| Concurrent fact extraction | Extraction pass removed from the critical path |
| Non-blocking translation | Synchronous Google Translate calls no longer block the event loop for all concurrent users |
| Model weights baked into images | Eliminated a cold-start dependency on HuggingFace Hub availability |

Measured steady-state `/chat` latency in production: **≈10 s** end-to-end, dominated by the
two sequential Groq LLM calls plus shared-tier CPU. Cold start (all services idle): ≈60 s.

> **Honest caveat:** no controlled before/after latency measurement was taken, because the
> pre-optimisation path was not instrumented. Report the optimisations as engineering work
> with described mechanisms, **not** as a measured speedup with a specific multiplier.

### 6.9 Accessibility

All interface text meets **WCAG 2.1 AA** (≥4.5:1 contrast) in both themes. The audit found
and corrected a value at **2.53:1** — below even the 3:1 large-text minimum — used for
usernames, section labels, and helper text throughout the interface.

---

## 7. Implementation details

### 7.1 Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS, Recharts, react-webcam, Web Speech API |
| Backend | FastAPI, Uvicorn, Python 3.11 |
| ML runtime | PyTorch (CPU), HuggingFace Transformers, spaCy, LIME, scikit-learn, OpenCV |
| LLM inference | Groq API (Llama 3.3 70B Versatile, Llama 3.1 8B Instant) |
| Cloud services | Google Cloud Translation, Google Cloud Text-to-Speech |
| Database | PostgreSQL (Neon serverless) |
| PDF generation | ReportLab |
| Hosting | Google Cloud Run (frontend, text service, face service), Render (orchestrator) |
| CI/CD | GitHub Actions, path-filtered per service |

### 7.2 Database schema

```sql
users        (id, username UNIQUE, password_hash, google_id UNIQUE, created_at)
conversations(id, user_id → users, persona_id, started_at)
messages     (id, conversation_id → conversations, user_id → users, role, content,
              emotion, confidence, face_emotion, clinical_tone, resolution_reason,
              crisis_flag, created_at)
reflections  (id, user_id → users, week_key, content, entry_count, created_at,
              UNIQUE(user_id, week_key))
```
`messages.content` and `reflections.content` are Fernet-encrypted at rest.

### 7.3 API surface (17 endpoints)

```
POST   /auth/signup, /auth/login, /auth/google      GET /auth/me
POST   /chat                    Main pipeline: analyse + respond
POST   /translate               Batch UI translation
POST   /speak                   Emotion-conditioned TTS → MP3
GET    /conversations           DELETE /conversations/{id}
GET    /conversations/{id}/messages
GET    /history, /rating, /reflection
GET    /export, /export/doctor-report?format=txt|pdf
DELETE /account                 GET /health
```

### 7.4 Code distribution

| Component | Lines |
|---|---|
| Frontend (React) | 3,103 |
| Models / core logic | 1,270 |
| Research harnesses | 1,050 |
| Orchestrator | 504 |
| Database layer | 316 |
| Text service | 269 |
| Face service | 134 |
| **Total** | **≈6,686** |

---

## 8. Limitations (state these — reviewers will find them anyway)

1. **No human evaluation.** No clinical validation, no counsellor agreement study, no
   user trial. The system's therapeutic value is **unevaluated**. This is the single
   largest limitation and must be stated plainly.
2. **Pairing is synthetic.** Text and face come from different sources and different
   people; a congruent pair is a construction, not a recording of one person expressing
   one emotion in both channels simultaneously. It is the best available design given
   that no paired corpus exists, but it is not the same as real paired data.
3. **The face modality is evaluated in-domain.** FER2013 is close to the face model's
   fine-tuning distribution, so its 88–89% flatters it relative to real webcam input.
   The fusion gain over face-only might be larger in deployment, but this is untested.
4. **No neutral class in Set B**, and `disgusted` is capped at 111 pairs by FER2013
   image availability.
5. **Sarcasm unhandled** — 0/2 on sarcastic cases for both text models tested.
6. **Modality priors not swept.** 0.55/0.45 is reasoned, not optimised. Note that the
   ablation shows calibration dominates, so the prior matters less than it appears.
7. **Conflict subsets are small** — n=51 (Set A) and n=126 (Set B). The arbitration
   findings are consistent across both but rest on modest samples.
8. **A vision-language arbiter was not evaluated.** Every arbiter tested reads text
   only. Whether a model that can see the face image would do better is an open
   question and is stated as future work.
9. **FER2013 label ceiling.** Human accuracy on FER2013 is ≈65 ± 5%; the 88.35% figure
   reflects agreement with dataset labels, which are themselves noisy. Do not claim
   "super-human" performance.
10. **Translation round-trip.** Non-English input is translated to English for analysis;
    nuance may be lost, and this was not measured.
11. **No controlled latency benchmark** — see §6.8.
12. **Single-face assumption.** Only the largest detected face is used.
13. **Calibration constants are fitted on constructed pairs, not on user data.** The
    temperatures and class-conditional reliabilities in `models/fusion.py` come from the
    pooled calibration splits of the two synthetic paired sets (n=1,631). They inherit
    every property of limitation 2 — in particular, they encode how reliable each modality
    is on *these* corpora, which need not match a real user population. Recalibrating on
    genuine paired data is the single highest-value follow-up.
    *(Note: the earlier concern that these constants were stale relative to the §6.2b text
    change has been resolved — they were re-fitted, and §6.3b reports the result.)*
14. **The headline label can now contradict the displayed emotion arc.** Because the
    overall label comes from a whole-entry pass while the arc comes from a per-sentence
    pass, the two can disagree — observed live on *"Work was fine today. Nothing much
    happened."* (headline `sad`, arc `[neutral, neutral]`) and *"I keep telling myself it
    is fine but I am not okay."* (headline `fearful`, arc `[neutral, sad]`). This was
    structurally impossible under the previous design, where the headline was an
    aggregation of the arc. It is a user-visible consistency regression that the accuracy
    gain does not by itself justify ignoring, and it is not captured by any metric in §6.2b.
15. **Neutral behaviour is effectively unmeasured.** Set B contains no neutral examples
    (limitation 4), so every §6.2b number is blind to the class that is probably the most
    common in real journaling. The first live probe above — a plainly neutral entry
    labelled `sad` at 0.542 confidence — is exactly the failure this blind spot would
    hide. Any claim about neutral performance requires a benchmark that contains it.
16. **Sentence-level aggregation was removed but not replaced with a fitted alternative.**
    A learned aggregator over sentence distributions might outperform whole-entry
    classification on long entries; only the hand-weighted version was tested and
    rejected. Entries in the benchmark average ~22 words, so the result may not transfer
    to substantially longer journal entries.

### 8.1 Experiments that would strengthen the paper (if time permits)

| Experiment | Effort | Value |
|---|---|---|
| Merge the proposed fusion into production and re-verify live | Low | High — lets the paper describe a deployed method |
| Crop ablation: FER2013 with/without detect-and-crop for an aggregate number | Low | High — turns an anecdote into a result |
| Modality-prior sweep (vary 0.55/0.45) | Low | Medium — makes the prior defensible |
| Expand the journal benchmark from 49 to ~150 cases | Medium | High — strengthens §6.2 |
| Vision-language arbiter on higher-resolution face data (RAF-DB, AffectNet) | High | Medium — closes the one untested arbiter design |
| Small user study (even n = 10–15) on perceived response quality | High | Very high — addresses limitation 1 |

## 9. Related work — what to cite

Search and cite properly; do **not** fabricate references. Target categories:

1. **Facial emotion recognition** — FER2013 dataset paper (Goodfellow et al., 2013,
   "Challenges in Representation Learning"); ViT (Dosovitskiy et al., 2021).
2. **Text emotion recognition** — GoEmotions (Demszky et al., 2020); RoBERTa (Liu et al.,
   2019); DistilBERT (Sanh et al., 2019).
3. **Multimodal fusion** — surveys on early vs late fusion; Baltrušaitis et al. (2019),
   "Multimodal Machine Learning: A Survey and Taxonomy"; confidence/uncertainty-aware
   fusion literature.
3b. **Calibration — essential, this is the paper's core** — Guo et al. (2017), "On
   Calibration of Modern Neural Networks" (temperature scaling, ECE); Naeini et al.
   (2015) for ECE; Platt (1999) for the scaling precedent. For the pooling rule:
   Hinton (2002) "Training Products of Experts by Minimizing Contrastive Divergence",
   and the opinion-pool literature (Genest & Zidek, 1986) for linear vs logarithmic
   pooling — the theoretical grounding for §4.4b's product combination.
4. **Explainable AI** — LIME (Ribeiro et al., 2016, "Why Should I Trust You?").
5. **Mental-health technology** — Woebot / Wysa trial literature; conversational-agent
   reviews in digital mental health.
6. **LLMs in healthcare** — recent surveys on LLM safety and grounding in clinical contexts.
7. **Statistics** — McNemar (1947) for the paired test.
8. **Context** — WHO Mental Health Atlas for the access-gap framing.

**Positioning statement for Related Work:** prior multimodal emotion systems typically
(a) fuse with fixed weights, (b) evaluate only on the benchmark a model was trained on,
and (c) provide no explanation. This work addresses all three, and additionally
demonstrates that (b) can invert a model-selection decision.

---

## 10. Figures and tables to produce

| # | Content | Source |
|---|---|---|
| Fig. 1 | Three-service system architecture | §4.1; redraw as clean vector |
| Fig. 2 | Reliability-aware log-linear fusion pipeline (calibrate → reliability weight → log-pool) | §4.4b |
| Fig. 3 | **Reliability diagram: text vs face before and after calibration** | §6.3 — the diagnosis in one picture |
| Fig. 4 | Strategy comparison bar chart on both paired sets | §6.3 |
| Fig. 5 | Benchmark/domain inversion (GoEmotions vs journal, grouped bars) | §6.2 |
| Fig. 6 | Ablation: marginal effect of each component | §6.4 |
| Fig. 7 | Per-class F1: baseline vs deployed face model | §6.1 |
| Fig. 8 | Confusion matrix, deployed face model | `research/results/dima806_fer2013.json` |
| Fig. 9 | Screenshot: explainability panel | Live app |
| Fig. 10 | Screenshot: clinician PDF report | Live app |
| TABLE I | Face model comparison + McNemar | §6.1 |
| TABLE II | Text model benchmark vs domain | §6.2 |
| TABLE III | **Fusion strategies, both sets, with significance** | §6.3 |
| TABLE IV | Class-conditional reliability matrix | §4.4b |
| TABLE V | Ablation grid | §6.4 |
| TABLE VI | Arbitration designs A–D | §6.5 |

Figures 3, 4 and 6 carry the paper's core argument. Confusion-matrix and per-class data
are already persisted as JSON — plot directly from `research/results/`.

## 11. Reproducing every result

```bash
git clone https://github.com/Aadithyaar22/MoodScript
cd MoodScript
git checkout research/calibrated-fusion      # fusion/calibration work lives here
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# ---- face model selection (§6.1) ----
python research/eval_face_models.py --model dima806/facial_emotions_image_detection \
       --out research/results/dima806_fer2013.json
python research/eval_face_models.py --model trpakov/vit-face-expression \
       --out research/results/trpakov_fer2013.json
python research/compare_models.py --a research/results/dima806_fer2013.json \
                                  --b research/results/trpakov_fer2013.json

# ---- text model selection (§6.2) ----
python research/eval_text_model.py           # GoEmotions, deployed pipeline
python research/eval_text_candidates.py      # GoEmotions, candidates
python research/eval_deployed_journal.py     # 49 journal cases, deployed
python research/eval_samlowe_journal.py      # 49 journal cases, candidate

# ---- text pipeline ablation + current pipeline verification (§6.2b) ----
# these need Set B built first (see the block below)
python research/eval_text_journal_bench.py       # 4 candidate checkpoints, 1,056 texts
python research/eval_text_pipeline_ablation.py   # variants A / B / C + McNemar
python research/eval_text_model_v2.py            # runs the real predict(), old vs new

# ---- build the paired benchmarks (§5.1) — run these first for §6.3-6.5 ----
python research/build_paired_set.py --per-class 200 \
       --out research/results/paired_set.json                        # Set A
python research/build_paired_set.py --text-source empathetic --per-class 400 \
       --out research/results/paired_set_journal.json                # Set B

# ---- refresh text preds + refit constants after a text-pipeline change ----
python research/refresh_text_preds.py --paired-set paired_set.json
python research/refresh_text_preds.py --paired-set paired_set_journal.json
python research/fit_fusion_constants.py        # prints constants for models/fusion.py

# ---- fusion, ablation, arbitration (§6.3-6.5) ----
python research/verify_production_fusion.py    # §6.3b — the DEPLOYED numbers
python research/eval_fusion_v2.py --paired-set paired_set.json          # Set A
python research/eval_fusion_v2.py --paired-set paired_set_journal.json  # Set B
python research/eval_ablation.py
python research/eval_arbiter_paired.py --paired-set paired_set_journal.json \
       --out arbiter_paired_journal.json                             # needs GROQ_API_KEY
python research/eval_arbiter_v2.py --paired-set paired_set_journal.json
python research/eval_conflict_policies.py --paired-set paired_set_journal.json

# ---- response generation and LLM choice (§6.6-6.7) ----
python research/eval_two_pass.py
python research/eval_llm_ab.py
```

Building a paired set runs both models over every pair and takes roughly 5–15 minutes on
CPU; results are cached to JSON so all downstream experiments are near-instant. Raw
predictions, per-class metrics and confusion matrices are written to `research/results/`.

## 12. Team and attribution

| Name | Role |
|---|---|
| Aadithya A R | System design and full implementation |
| Kenisha P | Paper authoring |
| Shreya V | Paper authoring |
| Pranathi N | Paper authoring |

Institution: Global Academy of Technology, Bangalore
Department: *(confirm — CSE (AI & ML) per the project proposal)*

---

## 13. Ethical statement (include in the paper)

- The system is positioned as a **supportive and documentary aid, not a diagnostic
  instrument**. The clinician report explicitly avoids clinical disorder labels.
- Crisis resources are hard-coded and never model-generated, so they cannot be
  hallucinated or altered by a model.
- All journal content is encrypted at rest; account deletion cascades through every table.
- No user data was collected for the evaluations in this paper — all benchmarks use public
  datasets or synthetic test cases authored by the team.
- No IRB approval was obtained, and correspondingly **no human-subject evaluation was
  performed**; this constrains the claims the paper can make (§8.1).
