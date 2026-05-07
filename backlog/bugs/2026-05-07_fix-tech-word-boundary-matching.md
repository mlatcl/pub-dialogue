---
id: "2026-05-07_fix-tech-word-boundary-matching"
title: "Fix tech-word filter to use word-boundary matching"
status: "Completed"
priority: "High"
created: "2026-05-07"
last_updated: "2026-05-07"
owner: ""
dependencies: []
related_cips: []
---

# Task: Fix tech-word filter to use word-boundary matching

## Description

In `dialogue_utils.py`, `extract_phrases()` filters out phrases containing
technology-specific words using a substring check:

```python
match = next(
    (tw for tw in tech_words if tw in phrase.lower()), None
)
```

This is a substring match, not a word-boundary match. As a result, short
tech words like `gm` (for "GM crops") match inside unrelated words:
- `"gm"` matches `"stigma"`, `"algorithm"`, `"programme"`, `"paradigm"`

This causes legitimate concern/benefit phrases to be silently dropped.

## Acceptance Criteria

- [ ] Tech-word matching uses `re.search(r'\b' + re.escape(tw) + r'\b', phrase.lower())` or equivalent
- [ ] All existing tests continue to pass
- [ ] New unit test added: verify `"stigma"` is NOT dropped by `gm` filter
- [ ] New unit test added: verify `"gm crops concern"` IS dropped by `gm` filter

## Implementation Notes

Replace in `extract_phrases`:

```python
# Before:
match = next(
    (tw for tw in tech_words if tw in phrase.lower()), None
)

# After:
import re
match = next(
    (tw for tw in tech_words
     if re.search(r'\b' + re.escape(tw) + r'\b', phrase.lower())),
    None,
)
```

Also review `tech_words` list for any other multi-character words that might
have similar false-positive issues.

## Related

- Review Issue 6b (substring false positives in tech-word filter)
- `dialogue_utils.py` — `extract_phrases`, line ~387

## Progress Updates

### 2026-05-07
Task created with Ready status based on review findings.
