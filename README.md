# Provenance Guard

Provenance Guard is a Flask-based prototype system that estimates whether submitted text is AI-generated or human-written. It combines an LLM-based signal (Groq) with a stylometric heuristic signal. It reports uncertainty instead of pretending that the result is proof, it records the decision of the system in its audit log, and also supports an appeal workflow.

## Demo

## Architecture Overview

### Submission flow

```
text
Submission Flow

[Client]
   |
   | raw text
   v
[POST /submit]
   |
   | raw text
   v
[Signal 1: Groq LLM Classification]
   |
   | signal score
   v
[Signal 2: Stylometric Heuristics]
   |
   | signal score
   v
[Confidence Scoring]
   |
   | combined score
   v
[Transparency Label Generator]
   |
   | label text
   v
[Audit Log]
   |
   | text, label, scores, metadata
   v
[Response to Client]
   |
   | label text + confidence
   v
[Platform Interface]
```

The two signals run on the same submitted text. The calculator combines their 0-1 AI-likelihood scores, records how much they disagree, and maps the result to one of three labels. The response includes the individual signal outputs, confidence, and the label is shown to the end user.

### Appeals flow

```
[Client]
   |
   | appeal reasoning + submission ID
   v
[POST /appeal]
   |
   | appeal data
   v
[Status Update]
   |
   | status: under review
   v
[Audit Log]
   |
   | appeal data + updated status
   v
[Response to Client]
   |
   | updated review status
   v
[Appeal Queue / Platform Interface]
```

An appeal doesn't silently overwrite the original decision. It preserves the original scores and adds the user's reasoning as a separate event for human review.

## Detection Signals

### 1. Groq LLM

The Groq signal asks `openai/gpt-oss-120b` for a structured
`ai_probability` between 0.00 and 1.00. The prompt asks the model to consider personal specificity, conversational language, generic or formulaic phrasing, repetition, sentence organization, editing, and mixed authorship. A score near 1 means the model sees more evidence for AI generation while a score near 0 means it sees more evidence for human writing.

This signal is useful because an LLM can assess semantic and rhetorical patterns that simple counts cannot: generic transitions, institutional boilerplate, coherence, and whether the writing sounds personally grounded. I intentionally had to make this signal weigh more heavily in the system since it covers a broader set of cues than the uncalibrated heuristic. It's not ground truth meaning model judgments can (and did) vary between requests and can mistake polished human writing, technical writing, or writing by a non-native English speaker for AI.

### 2. Stylometric Heuristics

This signal is local to Python and computes the following features:

- sentence-length standard deviation and sentence uniformity
- type-token ratio, a rough measure of vocabulary diversity
- punctuation density.

These features are useful since sentence uniformity captures highly regular generated prose, vocabulary diversity provides a coarse lexical signal, and punctuation density captures another surface-level pattern.

The current implementation is a bounded heuristic and not a calibrated probability. I had to shrink its score to `0.5` for short submissions because there is not enough text (like as a json of examples) for reliable statistical evidence. So I made the stylometric signal only 25% of the current blend. Its features are explainable, but they haven't been fitted and validated on any type of representative corpus that's been labeled.

### Why use both signals?

The signals fail in different ways. Groq had broader semantic coverage but was sometimes be inconsistent when I repeated requests. The stylometric heuristics are deterministic and explainable but were narrow and sensitive to genre and formatting. Agreement between the signals is more persuasive than either signal alone. Their disagreement is useful info that lowered confidence, rather than have it be hidden.

For a real deployment, I would have to collect (with consent) representative human and AI texts across different genres, of different lengths, that have accessibility tools, and different editing levels. I would have to calibrate each signal separately, analyze their individual error rates, and then retrain or replace the heuristic with a validated classifier.

## Confidence Scoring

Both signal outputs use the same direction: `0` means more likely human and `1` means more likely AI-generated. The system uses:

```
text
combined_score = 0.75 * groq_score + 0.25 * stylometric_score
disagreement = abs(groq_score - stylometric_score)
confidence = combined_score
             + (0.5 - combined_score) * 0.5 * disagreement
```

The 75/25 blend gives the broader Groq signal more influence while the stylometric signal remains an independent check. The disagreement value pulls a result toward neutral (`0.5`) when the signals conflict. I changed the disagreement handling from an automatic "uncertain if disagreement >= 0.25" because while I wanted disagreement to reduce certainty, I didn't want it to erase useful directional evidence in every case.

The current label thresholds are:

| Final confidence | Classification |
|---|---|
| `0.00-0.44` | High Confidence Human |
| `0.45-0.65` | Uncertain |
| `0.66-1.00` | High Confidence AI |

These were chosen to leave a neutral interval surrounding `0.5`, where either mixed authorship or conflicting evidence is possible (uncertainty).

### Variation examples

The following values are from the Milestone 4 four-text testing run after the prototype changed to the 75/25 blend and soft disagreement penalty:

| Submission | Groq | Stylometric | Combined | Disagreement | Final confidence | Result |
|---|---:|---:|---:|---:|---:|---|
| Test 1: "Artificial intelligence represents a transformative paradigm shift in modern society. It is important to note that while the benefits of AI are numerous, it is equally essential to consider the ethical implications. Furthermore, stakeholders across various sectors must collaborate to ensure responsible deployment." | `0.78` | `0.5156` | `0.7139` | `0.2644` | **`0.6856`** | High Confidence AI |
| Test 2: "ok so i finally tried that new ramen place downtown and honestly? underwhelming. the broth was fine but they put WAY too much sodium in it and i was thirsty for like three hours after. my friend got the spicy version and said it was better. probably won't go back unless someone drags me there" | `0.15` | `0.4995` | `0.2374` | `0.3495` | **`0.2833`** | High Confidence Human |

The scores are noticeably different with the first submission being pushed above the AI threshold by the strong Groq signal, while the second got pushed below the human threshold by its low Groq signal. The stylometric score stays near neutral in both examples, which is an important result to note. It shows that my system's current local heuristic doesn't understand enough context to distinguish those styles by itself.

For a real deployment, I wouldn't describe `0.6856` as a literal 68.56% probability until after calibration demonstrated that interpretation. I would fit Platt scaling or isotonic regression on held-out labeled data, choose the weights and thresholds using validation metrics, and report confidence intervals or an abstention policy. I would have to measure the false positives and negatives, calibration error, subgroup disparities, and the percentage of cases sent to review before enabling automated decisions.

## Transparency Label

The API returns exactly one of these typed variants:

* **High-confidence AI**
  `This text is highly likely AI generated.`
* **High-confidence human**
  `This text is highly likely to be human written.`
* **Uncertain**
  `This text may contain both AI generated content and actual human writing, one or the other is uncertain.`

My labels intentionally use “highly likely” rather than “proven.” The uncertain wording makes mixed authorship and disagreement visible to the user. In a production UI, each label would be accompanied by the score range, signal summaries, model/version metadata, and a clear appeal or human-review path. A user would always be aware as a disclaimer that the system detector cannot concretely determine authorship from text alone.

## API and Local Setup

Install dependencies in a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set `GROQ_API_KEY` in the environment or in a local `.env` file, then run:

```powershell
python app.py
```

### `POST /submit`

Request:

```json
{
  "text": "Text to classify.",
  "creator_id": "creator-1"
}
```

The response includes `content_id`, the Groq result, the stylometric result, the numeric `confidence`, and the transparency `label`.

### `POST /appeal`

Request:

```json
{
  "content_id": "the-id-returned-by-submit",
  "creator_reasoning": "I wrote this draft myself without any help from elswhere. The ideas are my own."
}
```

The response marks the matching classified entry as `under_review` and records an appeal event.

### `GET /log`

Returns the structured audit entries under an `entries` array. The prototype stores them in process memory, so restarting the server loses the log.

## Rate Limiting: Submission rate limits

`POST /submit` is limited to **10 requests per minute and 100 requests per day per client IP address**. The limits are scoped to submissions because each request runs the detection pipeline and can consume a Groq API request.

This policy supports ordinary drafting and retrying while preventing a script from continuously flooding the pipeline. Per-client limits also prevent one active writer from consuming a global allowance for everyone else.

The local server uses Flask-Limiter's `memory://` backend. A production deployment should use shared persistent storage such as Redis, account-aware quotas in addition to IP limits, proxy-aware client identification, and monitoring for bypasses. IP addresses alone are unreliable behind NAT, proxies, and shared networks.

### Verification evidence

With the Flask server running, 12 rapid `POST /submit` requests produced:

```text
200
200
200
200
200
200
200
200
200
200
429
429
```

The first ten requests were accepted and requests 11 and 12 were rejected with HTTP `429 Too Many Requests`.

## Audit Log and Verification

Each classification entry records a timestamp, unique `content_id`,
`creator_id`, attribution, final confidence, exact label, Groq score,
stylometric score, combined score, disagreement, status, and appeal state. When an appeal is submitted, the original entry becomes `under_review` and a separate appeal event stores the creator's reasoning. This gives a reviewer the inputs and intermediate values needed to reconstruct the decision.

Example classification entries:

```json
{
  "content_id": "d2c16f6c-4e34-4b71-9d3c-3cac68230aac",
  "timestamp": "2026-10-06T19:42:36.757Z",
  "attribution": "High Confidence Human",
  "confidence": 0.342752,
  "groq_score": 0.25,
  "stylometric_score": 0.522,
  "appeal_filed": false,
  "status": "classified"
}
```

For official production, the audit log should be durable, access-controlled, encrypted where appropriate, append-only or tamper-evident, and governed by a retention policy. The submitted text may contain personal or confidential information, so logging it or sending it to an external LLM requires clear privacy and data-processing decisions.

## Known Limitations

1. **Short messages, headlines, and single-sentence answers.**

  The stylometric signal has too few sentences and words to estimate sentence variation or vocabulary reliably, so it deliberately shrinks toward `0.5`. The result often leads to being uncertain or overly dependent on the Groq score.

2. **Poetry, song lyrics, and intentionally repetitive text.**

  Repetition and unusual punctuation can be meaningful artistic choices, but the signal treats type-token ratio, punctuation density, and sentence usualness as evidence. A human lyric such as a repeated chorus can therefore look artificially AI-like.

3. **Formal academic, legal, technical, or historical prose.**

  These genres naturally use standardized transitions, regular sentence structures, and dense punctuation. Those are the same surface properties the LLM prompt and stylometric features may associate with AI-generated writing, creating false AI positives. Older texts that use em dashes are another example of punctuation that should not be treated as provenance evidence.

4. **Multilingual writing, code-switching, and non-native English.** The local
   word extractor only recognizes ASCII-style English words, and both the
   type-token ratio and LLM judgment can change with language proficiency or
   translation. The system may mis-score the text or lack enough usable
   features.

5. **Edited, paraphrased, or mixed-authorship text.**

  Human editing can remove obvious generation patterns while leaving a polished structure, and combining human and AI passages gives no single true label. The two signals may disagree, but disagreement only moves the score toward neutral, it can't identify which span came from which author, human or AI.

6. **Adversarial rewriting.**

  A user can change sentence lengths, punctuation, or vocabulary without changing the underlying authorship. Because these are surface signals, changes like this can manipulate the final scores.

## Spec Reflection

The implementation followed what I wrote in planning.md.

* `POST /submit` runs Groq and stylometric detection before scoring.
* Scores are combined on a 0-1 scale and mapped to three transparency labels.
* `POST /appeal` records user reasoning and changes the original status to `under_review`.
* `GET /log` exposes structured evidence for traceability.
* Rate limiting protects the external-API-backed submission path.

What I had to change majorly from my original planning.md is how disagreement handling would work. Before, if disagreement between Groq and stylometric heuristics was >= 0.25, the label uncertain would automatically be Uncertain. This hard penalty affected a lot of clearly human or clearly AI text examples, especially since Groq qas inconsistent and the heuristics weren't calibrated for this project, so I changed it to a soft penalty where it will sawy the label towards neutral slightly instead of outrightly overruling as uncertain. I changed the weights of the signals from equal to 0.75 for Groq and 0.25 for stylometrics since due to the heuristics signal not being calibrated on any type of training data, it would usually alawys lean towards neutral. Both these changes got recorded in planning.md so that when I gave the context to Copilot in subsequent milestones, it knew why I changed things and could adjust code going forward accordingly.

## AI Usage

I used Copilot to help generate and revise the Flask skeleton, Groq signal, stylometric heuristics signal, confidence scoring logic, transparency labels, rate limiting, audit logging, and appeals endpoint. My planning.md and testing questions supplied the system's intended architecture and thresholds. I verified the generated work by inspecting the code, running the four test examples plus four of my own (eight total), checking that scores varied, exercised the rate limit, and verified that the audit and appeal state transitions were working.

I didn't accept what Copilot implemented without reviewing it first. Especially when in the testing phase using example texts, the testing exposed that the original stylometric features were too close to neutral for casual human writing and that the live LLM scores from Groq often varied from request to request. This made me ask Copilot what I could do to fix this practically, barring making a whole JSON of example texts to calibrate the signals (especially stylometric heuristics) on.
