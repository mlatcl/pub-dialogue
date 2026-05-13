---
id: "2026-05-13_retry-backoff-extract-phrases"
title: "Add retry with exponential backoff to extract_phrases"
status: "Completed"
priority: "High"
created: "2026-05-13"
last_updated: "2026-05-13"
category: "features"
related_cips: ["000E"]
owner: ""
dependencies: []
tags:
- extraction
- rate-limit
- robustness
---

# Task: Add retry with exponential backoff to extract_phrases

## Description

`extract_phrases` in `pub_dialogue/address.py` currently catches all exceptions and
returns an empty `ExtractionResult(error=...)` immediately. When OpenAI returns a
`RateLimitError` (HTTP 429), the chunk is permanently dropped.

On the 2026-05-12 run, 3,261 of 10,047 chunks (32.5%) were lost this way, causing
a hard `RuntimeError` stop and no output CSV written despite 13,188 phrases having
been successfully extracted.

Add a `_complete_with_retry()` helper that retries `client.complete()` on
`RateLimitError` with exponential backoff + jitter, and use it in `extract_phrases`.

## Acceptance Criteria

- [ ] `_complete_with_retry(client, messages, max_tokens, max_retries=5)` added to `pub_dialogue/address.py`
- [ ] `extract_phrases` uses `_complete_with_retry` instead of direct `client.complete`
- [ ] `extract_phrases` accepts `max_retries: int = 5` parameter (default preserves old behaviour)
- [ ] `litellm.RateLimitError` caught and retried; other exceptions still propagate to outer handler
- [ ] Backoff: starts at 1 s, doubles each attempt, caps at 60 s, adds ±0.5 s jitter
- [ ] Unit test: mock `RateLimitError` for first 3 calls, succeeds on 4th — verifies retry count and delay sequence
- [ ] Unit test: mock `RateLimitError` for all calls — verifies final `ExtractionResult.error` is set

## Implementation Notes

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
            delay = min(delay * 2, 60.0)
```

Also consider reducing `max_workers` in the ThreadPoolExecutor from 10 to 5 to
stay comfortably under the 500 RPM limit even without retry.

## Related

- CIP: 000E

## Progress Updates

### 2026-05-13
Task created following 32.5% rate-limit failure on full extraction run.
