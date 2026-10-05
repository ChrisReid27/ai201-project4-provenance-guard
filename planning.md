## Architecture Narrative

This is the path a single piece of text takes from submission to the label a user sees.

The text first enters the system through the `content submission` endpoint. Before processing starts, `rate limiting` is enforced on the request by the rate limiter, checking its IP address or API token against already defined thresholds to prevent attacks. If the request is above a max limit then too many requests gets returned, but if it's under then the request continues.

The `multi signal detection pipeline` analyzes the text using at least two types of signal detections: LLM based classification with Groq (usisng openai/gpt-oss-120b) and stylometric heuristics (computable within python). Groq asks the model to assess whether text reads as human or AI-generated and captures semantic and stylistic coherence holistically. Stylometric heuristics are measurable  statistical properties that differ between human and AI writing such as sentence length variance, type-token ratio (vocabulary diversity), punctuation density, or average sentence complexity. Blindspots are that Groq... and stylometric heuristics... Each signal analyzes the text and gives a raw score/feature vector detailing if the writing is human or AI based on if its close or not close to known AI-generated patterns vs human writing patterns.

The outputs from the detection pipeline get aggregated in the confidence calculator. It weighs the similarities and disimilarities of the two different signal scores from before and delivers its own final score between 0 and 1. High similarity between two signal scores gives `confidence scores` near 0 or 1, while conflicting scores from the signals gives confidence near 0.5 indicating `uncertainty`.

The `transparency label` generator recieves the confidence score from the confidence calculator and the classification. The score is mapped to one of three different predefined labels: High Confidence Human, High Confidence AI, or Uncertain. The first denotes high confidence of human written text, the second is high confidence for AI written text, and the third is for uncertain origin or potentially mixed written text.

At the same time label generation is happening, the `audit logger` records a permanent, structured entry containing the submission metadata, the individual signal outputs, the final confidence score, the timestamp, and the generated transparency label, ensureing complete traceability and accountability for every decision made by the system.

At the end, the text along with its designated transparency label is shown on the platform interface for the end user to see, giving them clear, contextual insight into the text's verified or estimated attribution status. But if the user disagrees with the assessment, they can submit an appeal through the `appeals workflow`. This workflow will capture the user's written reasoning, update the text's database status to "under review", and append the appeal data directly into the system's audit log alongside the original decision for human review.

## Planning

**Detection Signals**

**Uncertainty Representation**

**Transparency Label Design**

**Appeals Workflow**

**Anticipated Edge Cases**

## Architecure

**Diagram**

## AI Tool Plan

**M3 (submission endpoint + first signal)**

**M4 (second signal + confidence scoring)**

**M5 (production layer)**