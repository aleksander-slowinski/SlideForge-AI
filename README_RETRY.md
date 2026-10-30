# SlideForge v1.1 — A2: API Reliability patch

This is an additive, narrow patch for the prior A1 checkpoint update. It replaces the earlier version of `services/resumable_batch_service.py` and adds `services/api_retry_service.py` plus offline tests.

## Installation

Merge the `services/` and `tests/` folders into your SlideForge project on the `feature/long-presentations` branch. This does **not** change Streamlit, Classic mode, or `batch_content_service.py`.

## IMPORTANT: change the Gemini client in dev_test_batches.py

The application-level wrapper handles at most three attempts per **unfinished batch**. The SDK should not perform another independent retry loop. In `dev_test_batches.py`, ensure you have:

```python
from google.genai import types

client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(attempts=1),
    ),
)
```

If other callers pass their own Gemini client to `generate_content_resumable`, configure those clients likewise; the service can only set options for clients it creates itself.

## Test

```
python -m pytest tests/test_api_retry.py -v
python -m pytest -q
python dev_test_batches.py --full
```

## Behavior

- Retry only when an HTTP 503 or 429 is present as a typed exception (including when wrapped with `raise ... from`). No brittle regex on error message strings.
- Max 3 calls to `generate_batch` per unfinished batch, with exponential delays ~3 and ~6 seconds and up to 0.5s jitter.
- Never retry `400`, authentication failures, Pydantic errors, corrupted checkpoints, or other exceptions.
- The retry wrapper doesn't override or discard previously validated checkpoints.
- A persistent 503 will still cause an exception after 3 attempts. Re-run the same command to resume from the last checkpoint.
- Do not use two concurrent runs with the same plan/checkpoint directory.
- No automatic switch to another model: model is part of checkpoint fingerprint.
