---
author: "Neil Lawrence"
created: "2026-05-13"
id: "000E"
last_updated: "2026-05-13"
implemented: "2026-05-13"
status: "Implemented"
compressed: false
related_requirements: []
related_cips: ["000C", "000D"]
tags:
- cip
- extraction
- robustness
- logging
- testing
title: "Extraction Robustness: Retry, Logging, and Test Mode"
---

# CIP-000E: Extraction Robustness: Retry, Logging, and Test Mode

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [x] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected
- [ ] Deferred

## Summary

The concern and benefit extraction pipeline fails silently at scale due to three issues:
1. **No retry logic**: OpenAI rate-limit errors (HTTP 429) cause chunks to be permanently dropped rather than retried.
2. **Insufficient logging**: Errors are caught and stored in a CSV but not surfaced in a way that helps diagnosis during a run.
3. **No small-scale test mode**: There is no way to quickly validate the extraction pipeline on a handful of files/chunks before committing to a full 10,000-chunk run.

In the run on 2026-05-12, 3,261 of 10,047 chunks (32.5%) failed with `RateLimitError` (RPM limit 500), causing `RuntimeError` to be raised and the extracted CSV never written despite 13,188 phrases being successfully extracted.

## Motivation

The extraction pipeline runs 10,000+ chunks concurrently with 10 workers. At 500 RPM the burst easily exceeds the limit. Without retry logic every rate-limited chunk is permanently lost. Without visible logging, runs appear to complete but silently produce degraded output. Without a test mode, debugging requires a full multi-hour run.

## Detailed Description

### 1. Retry with exponential backoff

`extract_phrases` in `pub_dialogue/address.py` currently has a bare `except Exception` that records the error and returns an empty result. The fix is to wrap `client.complete()` with retry logic:

- Catch `litellm.RateLimitError` (and optionally `litellm.APIConnectionError`)
- Retry up to N times (default 5) with exponential backoff starting at 1 s, capped at 60 s
- Use jitter to avoid thundering-herd on concurrent workers
- Log each retry attempt at DEBUG level
- Only record as a permanent error after all retries exhausted

```python
import time, random

def _complete_with_retry(client, messages, max_tokens, max_retries=5):
    import litellm
    delay = 1.0
    for attempt in range(max_retries + 1):
        try:
            return client.complete(messages, max_tokens=max_tokens)
        except litellm.RateLimitError:
            if attempt == max_retries:
                raise
            time.sleep(delay + random.uniform(0, 0.5))
            delay = min(delay * 2, 60)
```

The `extract_phrases` signature gains optional `max_retries: int = 5`.

### 2. Structured logging

Add a Python `logging` logger (`logging.getLogger("pub_dialogue.address")`) to `pub_dialogue/address.py`. Log:

- `DEBUG`: each retry attempt with chunk_id, attempt number, and delay
- `WARNING`: permanent extraction failure with chunk_id and final error
- `INFO`: extraction batch summary (total, retained, errors)

The notebook sets log level via:
```python
import logging
logging.getLogger("pub_dialogue").setLevel(logging.WARNING)  # default
```

This replaces the litellm stderr noise with structured, filterable output.

### 3. Small-scale test mode in the notebook

Add a `TEST_MODE` constant near the top of `01_processing.ipynb`:
```python
TEST_MODE = False        # Set True to run on a small sample
TEST_N_DOCS = 3          # Number of source documents to include
```

When `TEST_MODE = True`, `chunks_df` is filtered to the first `TEST_N_DOCS` source files before extraction. This allows a quick end-to-end validation run in ~1 minute (tens of chunks rather than thousands).

### 4. Partial-cache re-run

The extraction cache (`extracted_concerns.json`) currently stores results for every chunk, including failed ones (with `"concerns": []`). On re-run, the cache key-check matches all chunks and the failed ones are silently skipped.

Add logic to detect stale/failed cache entries and re-run only those chunks:
```python
# Re-run chunks that previously returned 0 concerns AND had errors
if concerns_cache_file.exists():
    stale_ids = {k for k, v in cached_concerns.items()
                 if len(v["concerns"]) == 0 and k in previous_error_set}
    if stale_ids:
        # re-extract only stale_ids
```

## Implementation Plan

1. **Retry logic in `pub_dialogue/address.py`**:
   - Add `_complete_with_retry()` helper
   - Update `extract_phrases()` to use it with `max_retries` parameter
   - Add `logging` calls at DEBUG/WARNING level

2. **Structured logging setup**:
   - Add `logging.getLogger("pub_dialogue.address")` logger
   - Document log level configuration in notebook and README

3. **Test mode in `01_processing.ipynb`**:
   - Add `TEST_MODE` / `TEST_N_DOCS` constants
   - Add filter cell that subsets `chunks_df` when `TEST_MODE=True`

4. **Partial-cache re-run**:
   - Store per-chunk error flag in cache JSON
   - Add stale-entry detection and selective re-extraction

5. **Tests**:
   - Unit test retry logic (mock `RateLimitError` for first N calls)
   - Unit test that test-mode filter reduces chunk count correctly

## Backward Compatibility

- `extract_phrases` gains `max_retries=5` with default — existing callers unaffected.
- Cache JSON gains optional `"error": true` field per entry — existing caches remain loadable.
- `TEST_MODE = False` by default — notebooks behave identically unless opted in.

## Testing Strategy

- Mock `litellm.RateLimitError` in `tests/test_address.py` to verify retry behaviour.
- Verify that after max retries the function returns `ExtractionResult(error=...)`.
- Verify that `TEST_MODE=True` reduces `chunks_df` length.

## Related Requirements

None yet assigned.

## Implementation Status

- [x] Add `_complete_with_retry()` to `pub_dialogue/address.py`
- [x] Update `extract_phrases()` to use retry helper (with `max_retries=5` default)
- [x] Add structured logging to `pub_dialogue/address.py` (`pub_dialogue.address` logger)
- [ ] Add `TEST_MODE` constants and filter to `01_processing.ipynb`
- [x] Add partial-cache re-run logic to extraction cell (re-runs chunks in errors CSV)
- [x] Write unit tests for retry (`TestCompleteWithRetry`, `TestExtractPhrasesRetry` — 6 tests, all pass)
- [x] Reduce `max_workers` from 10 to 5 and suppress LiteLLM noise in extraction cells
- [x] Remove hard `RuntimeError` on failure-rate threshold — replaced with `show_warning`

## References

- `pub_dialogue/address.py` — `extract_phrases()`
- `01_processing.ipynb` — extraction cell (Cell ~60)
- `outputs/extraction_errors_concern.csv` — 3,261 `RateLimitError` entries from 2026-05-12 run
