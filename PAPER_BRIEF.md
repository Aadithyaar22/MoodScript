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
        C. Confidence-Weighted Fusion
        D. LLM Arbitration
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

1. *MoodScript: Confidence-Weighted Multimodal Emotion Recognition with LLM Arbitration for Explainable Mental-Health Journaling*
2. *An Explainable Multimodal Emotion-Aware Journaling System with Selective Language-Model Conflict Arbitration*
3. *Beyond Benchmark Accuracy: Domain-Validated Multimodal Emotion Recognition for Mental-Health Support*

Title 3 is worth serious consideration — the benchmark-versus-domain finding (§6.2) is
arguably the paper's most novel and defensible contribution.

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

1. **A confidence-weighted late-fusion strategy** in which each modality's influence is
   scaled by its own per-sample prediction confidence rather than a fixed prior, improving
   the calibration of the fused confidence score (§6.3).
2. **A selective LLM-arbitration layer** invoked only when numeric fusion reports an
   unresolved conflict, so the expensive path handles the minority of ambiguous cases
   while the deterministic path handles the rest (§4.4).
3. **A two-pass response generation scheme** that extracts concrete facts before
   generating, measurably increasing content-specificity (§6.4).
4. **An empirical demonstration that public-benchmark ranking can invert under
   domain shift** for emotion classification — the candidate model that wins on
   GoEmotions by 26 points loses on journal-style text (§6.2). This is a
   methodological contribution generalisable beyond this system.
5. **A complete, deployed, explainable system** integrating the above with
   LIME explainability, rule-based crisis detection, multilingual support, and
   clinician-readable report generation.

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
| Sentence segmentation | spaCy `en_core_web_sm` |
| Explainability | LIME (`LimeTextExplainer`) |
| Secondary signal | `SamLowe/roberta-base-go_emotions` → clinical tone (anxiety / depression / stress / positive / confusion / curiosity) |

**Processing:** the entry is segmented into sentences; each sentence is classified
independently; per-sentence results are aggregated with position, length, and confidence
weighting to produce an overall distribution plus a per-sentence *emotion arc*.

**Negation dampening (own contribution).** A syntax-aware correction using spaCy's
dependency parse. The rule fires **only** on negation of an auxiliary-headed adjectival
complement (`acomp`), e.g. *"I am **not** happy"*. This narrow scoping matters: an initial
broad implementation that dampened on *any* `neg` dependency also caught idiomatic negated
verbs that do **not** invert sentiment (*"can't stop crying"*, *"won't listen"*) and
**reduced** journal-domain accuracy from 72% to 61%. Restricting to AUX-headed `acomp`
negation raised it from 72% to 78% with no regressions. **This failed-then-fixed result is
worth reporting** — it is concrete evidence that naive negation handling is harmful.

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

Triggered **only** when `resolution_reason` starts with `conflict_resolved_to_` — i.e.
both modalities disagree with comparable confidence and numeric blending cannot settle it.

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
| **Deployed** (`j-hartmann` distilroberta + negation dampening) | 43.75% | **77.6% (38/49)** |
| `SamLowe/roberta-base-go_emotions` | **69.65%** | 71.4% (35/49) |
| `j-hartmann/emotion-english-roberta-large` | 47.34% | not evaluated |

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

### 6.3 Fusion strategy comparison

Evaluated on 8 constructed conflict scenarios (`research/results/fusion_comparison.json`).

**Result — state this precisely and honestly:** confidence-weighted fusion and naive
fixed-weight fusion select the **same top-1 emotion in every scenario tested**. The
difference is in the **confidence value assigned**:

| Scenario | Naive confidence | Confidence-weighted | Effect |
|---|---|---|---|
| Confident text, flat/uncertain face | 0.548 | **0.732** | Confident reading preserved rather than diluted |
| Flat/uncertain text, confident face | 0.474 | **0.704** | Confident reading preserved rather than diluted |
| Both confident, agree | 0.936 | 0.937 | Unchanged (as designed) |
| Both confident, disagree | 0.504 | 0.509 | Essentially unchanged |

**Why this matters despite unchanged top-1:** downstream behaviour keys off the confidence
value, not just the label — the arbitration trigger, and the low-confidence hedging mode in
response generation (threshold 0.45). Better-calibrated confidence therefore changes system
behaviour even when the label is identical.

**Do not overclaim this.** The honest statement is: *"confidence-weighted fusion improves
the calibration of the fused confidence score without altering top-1 accuracy on the
constructed conflict cases; a larger labelled multimodal set would be required to
demonstrate a top-1 accuracy effect."*

One scenario is instructive: a real captured case where the face model returned Happy 42% /
Fearful 41% / Angry 0% for an exaggerated angry expression. **Neither** fusion strategy
recovers the correct label — confirming that fusion cannot repair a confidently wrong
modality, which is precisely why the face-model swap (§6.1) was a separate necessary fix.

### 6.4 Two-pass response generation

Entity-hit-rate = fraction of concrete entities from the input referenced in the reply.

| Configuration | Entity-hit-rate |
|---|---|
| Single-pass | 0.35 |
| Two-pass (extraction → generation) | **0.60** |

A 71% relative improvement in content-specificity.

### 6.5 Conversational LLM selection

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

### 6.6 System engineering results

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

### 6.7 Accessibility

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

1. **No human evaluation.** No clinical validation study, no counsellor agreement study,
   no user trial. The system's therapeutic value is **unevaluated**. This is the single
   largest limitation and must be stated plainly.
2. **Fusion evaluated on constructed cases.** The 8 fusion scenarios are hand-built, not
   drawn from a labelled multimodal corpus. No public dataset provides paired
   journal-text + facial-image emotion labels, which is why this was done — but it limits
   the strength of the fusion claim.
3. **Arbitration not quantitatively evaluated.** The LLM arbitration layer's accuracy on
   conflict cases has not been measured against ground truth.
4. **Sarcasm unhandled.** 0/2 on sarcastic cases for both text models tested.
5. **Modality priors not swept.** The 0.55/0.45 split is reasoned, not optimised.
6. **Small LLM A/B sample.** n = 4.
7. **FER2013 ceiling.** Human accuracy on FER2013 is ≈65 ± 5%; the 88.35% figure reflects
   agreement with dataset labels, which are themselves noisy. Do not claim
   "super-human" performance.
8. **Translation round-trip.** Non-English input is translated to English for analysis;
   emotional nuance may be lost in translation, and this effect was not measured.
9. **No formal latency benchmark.** See §6.6.
10. **Single-face assumption.** Only the largest detected face is used.

### 8.1 Experiments that would strengthen the paper (if time permits)

Roughly in order of value per effort:

| Experiment | Effort | Value |
|---|---|---|
| Crop ablation: run FER2013 composites with/without detect-and-crop for an aggregate number | Low | High — turns an anecdote into a result |
| Arbitration accuracy on labelled conflict cases | Medium | High — currently unquantified |
| Modality-prior sweep (vary 0.55/0.45, plot accuracy/calibration) | Low | Medium — makes the prior defensible |
| Expand the journal benchmark from 49 to ~150 cases | Medium | High — strengthens the headline finding |
| Small user study (even n = 10–15) on perceived response quality | High | Very high — addresses limitation 1 |

---

## 9. Related work — what to cite

Search and cite properly; do **not** fabricate references. Target categories:

1. **Facial emotion recognition** — FER2013 dataset paper (Goodfellow et al., 2013,
   "Challenges in Representation Learning"); ViT (Dosovitskiy et al., 2021).
2. **Text emotion recognition** — GoEmotions (Demszky et al., 2020); RoBERTa (Liu et al.,
   2019); DistilBERT (Sanh et al., 2019).
3. **Multimodal fusion** — surveys on early vs late fusion; Baltrušaitis et al. (2019),
   "Multimodal Machine Learning: A Survey and Taxonomy"; confidence/uncertainty-aware
   fusion literature.
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
| Fig. 1 | Three-service system architecture | §4.1 diagram; regenerate as a clean vector figure |
| Fig. 2 | Confidence-weighted fusion data flow | §4.4 equations |
| Fig. 3 | Per-class F1: baseline vs deployed face model | §6.1 table |
| Fig. 4 | Benchmark/domain inversion (grouped bars: GoEmotions vs journal) | §6.2 — **the paper's key figure** |
| Fig. 5 | Confusion matrix, deployed face model | `research/results/dima806_fer2013.json` |
| Fig. 6 | Screenshot: explainability panel | Live app |
| Fig. 7 | Screenshot: clinician PDF report | Live app |
| TABLE I | Face model comparison + McNemar | §6.1 |
| TABLE II | Text model benchmark vs domain | §6.2 |
| TABLE III | Fusion calibration comparison | §6.3 |
| TABLE IV | LLM A/B | §6.5 |

Confusion-matrix data is already persisted in the results JSON — plot directly from it.

---

## 11. Reproducing every result

```bash
git clone https://github.com/Aadithyaar22/MoodScript
cd MoodScript
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Face model benchmark (FER2013 test split, ~10 min CPU per model)
python research/eval_face_models.py --model dima806/facial_emotions_image_detection \
       --out research/results/dima806_fer2013.json
python research/eval_face_models.py --model trpakov/vit-face-expression \
       --out research/results/trpakov_fer2013.json

# Paired significance test
python research/compare_models.py --a research/results/dima806_fer2013.json \
                                  --b research/results/trpakov_fer2013.json

# Text: public benchmark and domain benchmark
python research/eval_text_model.py          # GoEmotions, deployed pipeline
python research/eval_text_candidates.py     # GoEmotions, candidates
python research/eval_deployed_journal.py    # 49 journal cases, deployed
python research/eval_samlowe_journal.py     # 49 journal cases, candidate

# Fusion, arbitration, two-pass, LLM A/B
python research/eval_fusion.py
python research/eval_arbiter.py
python research/eval_two_pass.py
python research/eval_llm_ab.py              # needs GROQ_API_KEY
```

Raw predictions, per-class metrics, and confusion matrices for every run are written to
`research/results/`.

---

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
