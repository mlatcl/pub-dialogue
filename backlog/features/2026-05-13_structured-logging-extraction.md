---
id: "2026-05-13_structured-logging-extraction"
title: "Add structured logging to pub_dialogue extraction pipeline"
status: "Completed"
priority: "High"
created: "2026-05-13"
last_updated: "2026-05-13"
category: "features"
related_cips: ["000E"]
owner: ""
dependencies: []
tags:
- logging
- extraction
- diagnostics
---

# Task: Add structured logging to pub_dialogue extraction pipeline

## Description

Currently `extract_phrases` catches all exceptions silently and errors only surface
in the post-run `extraction_errors_concern.csv`. During a run the only signal is the
litellm "Give Feedback / Get Help" stderr noise, which provides no context about
which chunk failed or why.

Add a Python `logging` logger to `pub_dialogue/address.py` so that:
- Retry attempts are visible at DEBUG level
- Permanent failures are logged at WARNING with chunk_id and error type
- Batch summary (total / retained / errors) is logged at INFO after extraction

## Acceptance Criteria

- [ ] `logger = logging.getLogger("pub_dialogue.address")` added to `pub_dialogue/address.py`
- [ ] Each retry attempt logs at DEBUG: `"chunk %s: retry %d after %.1fs (RateLimitError)"`
- [ ] Permanent failure logs at WARNING: `"chunk %s: extraction failed — %s"`
- [ ] `write_extraction_diagnostics` logs batch summary at INFO
- [ ] Notebook sets `logging.getLogger("pub_dialogue").setLevel(logging.WARNING)` by default
- [ ] Notebook can be switched to DEBUG with a single line change
- [ ] litellm's own noisy logging suppressed: `logging.getLogger("LiteLLM").setLevel(logging.ERROR)`

## Implementation Notes

In `pub_dialogue/address.py`:
```python
import logging
logger = logging.getLogger("pub_dialogue.address")
```

In the notebook setup cell:
```python
import logging
logging.basicConfig(format="%(levelname)s [%(name)s] %(message)s")
logging.getLogger("pub_dialogue").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.ERROR)   # suppress litellm noise
```

## Related

- CIP: 000E

## Progress Updates

### 2026-05-13
Task created.
