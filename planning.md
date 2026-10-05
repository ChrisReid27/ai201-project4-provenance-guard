## Architecture Narrative

This is the path a single piece of text takes from submission to the label a user sees.

The text first enters the system through the `content submission` endpoint. Before processing starts, `rate limiting` is enforced on the request by the rate limiter, checking its IP address or API token against already defined thresholds to prevent attacks. If the request is above a max limit then too many requests gets returned, but if it's under then the request continues.

The `multi signal detection pipeline` analyzes the text using at least two types of signal detections: LLM based classification with Groq (usisng openai/gpt-oss-120b) and stylometric heuristics (computable within python). Groq asks the model to assess whether text reads as human or AI-generated and captures semantic and stylistic coherence holistically. Stylometric heuristics are measurable statistical properties that differ between human and AI writing such as sentence length variance, type-token ratio (vocabulary diversity), punctuation density, or average sentence complexity. Blindspots are that Groq... and stylometric heuristics... Each signal analyzes the text and gives a raw score/feature vector detailing if the writing is human or AI based on if its close or not close to known AI-generated patterns vs human writing patterns.

The outputs from the detection pipeline get aggregated in the confidence calculator. It weighs the similarities and disimilarities of the two different signal scores from before and delivers its own final score between 0 and 1. High similarity between two signal scores gives `confidence scores` near 0 or 1, while conflicting scores from the signals gives confidence near 0.5 indicating `uncertainty`.

The `transparency label` generator recieves the confidence score from the confidence calculator and the classification. The score is mapped to one of three different predefined labels: High Confidence Human, High Confidence AI, or Uncertain. The first denotes high confidence of human written text, the second is high confidence for AI written text, and the third is for uncertain origin or potentially mixed written text.

At the same time label generation is happening, the `audit logger` records a permanent, structured entry containing the submission metadata, the individual signal outputs, the final confidence score, the timestamp, and the generated transparency label, ensureing complete traceability and accountability for every decision made by the system.

At the end, the text along with its designated transparency label is shown on the platform interface for the end user to see, giving them clear, contextual insight into the text's verified or estimated attribution status. But if the user disagrees with the assessment, they can submit an appeal through the `appeals workflow`. This workflow will capture the user's written reasoning, update the text's database status to "under review", and append the appeal data directly into the system's audit log alongside the original decision for human review.

## Planning

**Detection Signals**

My two detection signals are LLM based classification (Groq) and stylometric heuristics. LLM based classification will measure whether text reads as human or AI-generated and captures semantic and stylistic coherence holistically. Stylometric heuristics will measure statistical properties that differ between human and AI writing like sentence length, vocab diversity, amount of punctuation, or average sentence complexity. To gel with how the confidence calculator will aggregate scores with its 0.0-1.0 scale, both of the detection signals will also use the 0.0-1.0 scale.

**Uncertainty Representation**

A score of 0.6 for my system woull most likely mean uncertain, probably similar for 0.4 as well. Raw signal output will get mapped to a calibrated score by... The threshhold that separates "likely AI" from "uncertain" from "likely human would be...

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

## AI Tool Plan

**M3 (submission endpoint + first signal)**

**M4 (second signal + confidence scoring)**

**M5 (production layer)**