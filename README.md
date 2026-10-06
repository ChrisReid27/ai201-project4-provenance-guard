# Provenance Guard

## Submission rate limits

The `POST /submit` endpoint is limited to **10 requests per minute and 100
requests per day per client IP address**. These limits are intentionally scoped
to submissions, since each request invokes the detection pipeline and can
consume an external Groq API request.

The limits support a realistic writer workflow: ten submissions per minute
allows a writer to retry, revise, and compare several drafts without waiting,
while 100 submissions per day accommodates a heavy day of drafting and testing.
At the same time, the policy prevents a script from continuously flooding the
pipeline: a client sending one request every few seconds reaches the per-minute
limit, and the daily cap bounds sustained automated use. The limits are
per-client-IP rather than global, so one active writer cannot exhaust the
allowance for everyone else.

For local development, Flask-Limiter uses its in-memory storage backend
(`memory://`). This is suitable for a single development process, but a
production deployment should use shared persistent rate-limit storage so the
limits remain consistent across workers and restarts.

### Verification evidence

With the Flask server running, 12 rapid `POST /submit` requests produced the
following status-code output:

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

The first ten requests were accepted, and requests 11 and 12 were rejected by
the per-minute limiter with HTTP `429 Too Many Requests`.

## Audit log verification

The `GET /log` endpoint returns structured JSON under an `entries` array. Each
classification entry records the timestamp, unique content ID, attribution
result, combined confidence score, Groq score, stylometric score, and explicit
appeal state. An appeal changes the original entry to `under_review` and sets
`appeal_filed` to `true`; a separate appeal event preserves the submitted
reasoning.

The following three classification entries were generated for documentation.
The second entry was appealed, so its status and `appeal_filed` value show the
updated state:

```json
[
  {
    "content_id": "d2c16f6c-4e34-4b71-9d3c-3cac68230aac",
    "timestamp": "2026-10-06T19:42:36.757Z",
    "attribution": "High Confidence Human",
    "confidence": 0.342752,
    "groq_score": 0.25,
    "stylometric_score": 0.522,
    "appeal_filed": false,
    "status": "classified"
  },
  {
    "content_id": "c19402ac-c586-416c-83b0-3cb70fa54dab",
    "timestamp": "2026-10-06T19:42:36.759Z",
    "attribution": "High Confidence Human",
    "confidence": 0.341829875,
    "groq_score": 0.25,
    "stylometric_score": 0.519,
    "appeal_filed": true,
    "status": "under_review"
  },
  {
    "content_id": "dad86b72-7149-4af4-9000-51f0393a4297",
    "timestamp": "2026-10-06T19:42:36.761Z",
    "attribution": "High Confidence Human",
    "confidence": 0.3460378046875,
    "groq_score": 0.25,
    "stylometric_score": 0.5327500000000001,
    "appeal_filed": false,
    "status": "classified"
  }
]
```

The corresponding structured appeal event contains the same content ID,
`event: "appeal"`, `status: "under_review"`, `appeal_filed: true`, a timestamp,
and the creator's `appeal_reasoning`.
