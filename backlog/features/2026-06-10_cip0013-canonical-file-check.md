---
id: "2026-06-10_cip0013-canonical-file-check"
title: "Add canonical-file check to assign_framing_lenses() in pub_dialogue/address.py"
status: "Proposed"
priority: "High"
created: "2026-06-10"
last_updated: "2026-06-10"
category: "features"
related_cips: ["0013"]
owner: ""
dependencies: []
tags:
- backlog
- framing-lenses
- reproducibility
- cip0013
---

# Task: Add canonical-file check to assign_framing_lenses()

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Modify `assign_framing_lenses()` in `pub_dialogue/address.py` to check for a
committed canonical JSON file before hitting either the run-output cache or the
LLM.

The lookup order becomes:
1. `pub_dialogue/lens_mapping_canonical_<kind>.json` — committed, version-controlled (NEW)
2. `outputs/[benefit_]framing_lens_mappings.json` — existing run-output cache (unchanged)
3. LLM call — existing fallback (unchanged, but add a `logging.warning` prompting the user to copy the result to the canonical path)

The canonical file path is resolved relative to `Path(__file__).parent` (the
`pub_dialogue/` package directory), so it works regardless of notebook working
directory.

## Acceptance Criteria

- [ ] When `pub_dialogue/lens_mapping_canonical_concern.json` exists and has full
      coverage, `assign_framing_lenses(kind='concern', ...)` returns it without
      calling the LLM or touching the outputs cache
- [ ] When only the outputs cache exists (no canonical file), existing behaviour
      is preserved
- [ ] When neither exists, the LLM is called, the result is written to
      `outputs/framing_lens_mappings.json`, and a `logging.WARNING` message is
      emitted telling the user to copy the file to the canonical path
- [ ] The same logic applies symmetrically for `kind='benefit'`
- [ ] No changes are required to `01a_clustering.ipynb` cells 36 or 54 (they
      inherit the new behaviour automatically via the `AddressStage` façade)

## Implementation Notes

Add before the existing outputs-cache block in `assign_framing_lenses()`:

```python
import logging
from pathlib import Path as _Path

_pkg_dir = _Path(__file__).parent
canonical_path = _pkg_dir / f"lens_mapping_canonical_{kind}.json"

if canonical_path.exists():
    logging.info(
        "assign_framing_lenses: loading canonical %s lens mapping from %s",
        kind, canonical_path,
    )
    with open(canonical_path) as f:
        return json.load(f)
```

After the existing LLM call and before returning, add:

```python
logging.warning(
    "assign_framing_lenses: no canonical %s lens mapping found. "
    "Generated from LLM and written to %s. "
    "Review this file and copy it to pub_dialogue/lens_mapping_canonical_%s.json "
    "to stabilise the mapping across runs.",
    kind, out_file, kind,
)
```

## Related

- CIP: 0013
- PRs:
- Documentation:

## Progress Updates

### 2026-06-10

Task created following acceptance of CIP-0013.
