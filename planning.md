## Architecture Narrative

This is the path a single piece of text takes from submission to the label a user sees.

The text first enters the system through the `content submission` endpoint. Before processing starts, `rate limiting` is enforced on the request by the rate limiter, checking its IP address or API token against already defined thresholds to prevent attacks. If the request is above a max limit then too many requests gets returned, but if it's under then the request continues.

The `multi signal detection pipeline` analyzes the text using at least two types of signal detections: LLM based classification with Groq (using openai/gpt-oss-120b) and stylometric heuristics (computable within python). Groq asks the model to assess whether text reads as human or AI-generated and captures semantic and stylistic coherence holistically. Stylometric heuristics are measurable statistical properties that differ between human and AI writing such as sentence length variance, type-token ratio (vocabulary diversity), punctuation density, or average sentence complexity. Blindspots for Groq are that it may produce false positives for polished, formal, short, multilingual, or domain/subject-specific human writing, and false negatives when generated text has been edited, paraphrased, or mixed with human writing. Blindspots for stylometric heuristics would be misclassifing legitimate writing due to genre, dialect, language proficiency, accessibility tools, editing software, and intentional stylistic choices affecting the features it measures. They are less reliable on short texts and can be manipulated by changing sentence structure or punctuation. Each signal analyzes the text and gives a raw score/feature vector detailing if the writing is human or AI based on if its close or not close to known AI-generated patterns vs human writing patterns. Neither signal can prove AI vs human writing perfectly, they only serve to provide probability based evidence.

The outputs from the detection pipeline get aggregated in the confidence calculator. It weighs the similarities and disimilarities of the two different signal scores from before and delivers its own final score between 0 and 1. High similarity between two signal scores gives `confidence scores` near 0 or 1, while conflicting scores from the signals gives confidence near 0.5 indicating `uncertainty`.

The `transparency label` generator recieves the confidence score from the confidence calculator and the classification. The score is mapped to one of three different predefined labels: High Confidence Human, High Confidence AI, or Uncertain. The first denotes high confidence of human written text, the second is high confidence for AI written text, and the third is for uncertain origin or potentially mixed written text.

At the same time label generation is happening, the `audit logger` records a permanent, structured entry containing the submission metadata, the individual signal outputs, the final confidence score, the timestamp, and the generated transparency label, ensureing complete traceability and accountability for every decision made by the system.

At the end, the text along with its designated transparency label is shown on the platform interface for the end user to see, giving them clear, contextual insight into the text's verified or estimated attribution status. But if the user disagrees with the assessment, they can submit an appeal through the `appeals workflow`. This workflow will capture the user's written reasoning, update the text's database status to "under review", and append the appeal data directly into the system's audit log alongside the original decision for human review.

## Planning

**Detection Signals**

My two detection signals are LLM based classification (Groq) and stylometric heuristics. LLM based classification will measure whether text reads as human or AI-generated and captures semantic and stylistic coherence holistically. Stylometric heuristics will measure statistical properties that differ between human and AI writing like sentence length, vocab diversity, amount of punctuation, or average sentence complexity. To gel with how the confidence calculator will aggregate scores with its 0.0-1.0 scale, both of the detection signals will also use the 0.0-1.0 scale.

**Uncertainty Representation**

A score of 0.6 for my system will be deemed uncertain by my system. Values surrounding 0.5 (max uncertainty or mixed signal) will most likely be marked uncertain (0.45-0.5 and then 0.5-0.65). Raw signal output will get mapped to a calibrated score by using a labeled calibration dataset where each signal gets calibrated separately before combining. The threshhold that separates "likely AI" from "uncertain" from "likely human would be:
- `0.00–0.44`: High Confidence Human
- `0.45–0.65`: Uncertain
- `0.66–1.00`: High Confidence AI

- **Steps for calibration:**
1. **Groq score:** Groq will return a structured score indicating how likely the text is AI-generated.
2. **Stylometric score:** A logistic regression model will convert the stylometric feature vector into an AI-likelihood score.
3. **Combination:** The two calibrated scores will be combined using a weighted model:

   The initial prototype will use `combined_score = 0.75 * groq_score + 0.25 * stylometric_score` to limit interference from uncalibrated stylometric fallback.

5. **Signal disagreement:** The system will also calculate:

   `disagreement = abs(groq_score - stylometric_score)`

   (A large disagreement will lower the confidence, even if the combined score is high or low.)

The prototype applies disagreement as a soft confidence penalty that moves the combined score toward neutral: `confidence = combined_score + (0.5 - combined_score) * 0.5 * disagreement`, rather than making every disagreement of `0.25` or higher automatically `Uncertain`. The raw scores, combined score, disagreement value, and final label will get stored in the audit log.

**Transparency Label Design**

The text that will be shown for likely AI would be "This text is highly likely AI generated."
For likely human it would say "This text is highly likely to be human written."
For uncertain it would say "This text may contain both AI generated content and actual human writing, one or the other is uncertain."

**Appeals Workflow**

A user who disagrees with the systems final classification conclusion can submit an appeal. They would need to provide reasoning as to why they disagree and/or share the intended purpose of the original text (summarized again, in a way). The system would update the text's database status to "under review", and appeal data would get appended directly into the audit log alongside the original decision for human review. When the user opens the appeal queue they would see the under review status and when finished the new result.

**Anticipated Edge Cases**

- Songs that feature heavy use of repetion. Example: Everything Is Romantic by charli xcx where "fall in love again and again" is repeated many, many times.

- Passages from older books and texts that use em-dashes. Em-dashes are an extremely easy tell of AI use or genereated content so a lot of human writers avoid them now. The system will probably flag em-dashes via stylometric heuristics which track punctuations like this.


## Architecure

**Diagram**

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


Appeal Flow

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
- **Diagram Summary**:

The submission workflow receives raw text through `POST /submit`, then processes it through the Groq and stylometric signals, combines their calibrated scores, generates a transparency label, and then records the decision in the audit log before returning the result to the user. The appeals workflow receives the user's reasoning through `POST /appeal`, changes the submission status to `under review`, records the appeal alongside the original decision, and returns the updated status for human review.

## AI Tool Plan

**M3 (submission endpoint + first signal)**

I'll give Copilot/Claude my detection signals and architecture diagram and ask it to generate the skelton of my Flask app and the first signal function (Groq). I'll verify the output by testing a few inputs directly before wiring it into the submission endpoint.

**M4 (second signal + confidence scoring)**

I'll next give Copilot/Claude my detection signals, diagram, and my uncertainty representation sections and ask it to generate the second signal function (stylistic heuristics) and also the scoring logic. For verification, I'll check to see if the scores vary enough between clearly AI and clearly human text.

**M5 (production layer)**

I'll lastly give Copilot/Claude my diagram with my appeals workflow and label variants sections and ask for label generation logic and the appeal endpoint. I'll verify by testing that all three labels (HC Human, HC AI, and Uncertain) are reachable and than an appeal updates status to "under review" correctly.