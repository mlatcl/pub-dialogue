---
id: "2026-05-14_cip0012-load-prompts-and-wire"
title: "Add load_prompts() and replace hardcoded prompt constants in address.py"
status: "Proposed"
priority: "High"
created: "2026-05-14"
last_updated: "2026-05-14"
category: "features"
related_cips: ["0012"]
owner: ""
dependencies: ["2026-05-14_cip0012-create-prompts-yml"]
tags:
- backlog
- prompts
- address
- cip0012
---

# Task: Add load_prompts() and wire up constants in address.py

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Add a `load_prompts(path=None)` function to `pub_dialogue/address.py` that reads
`pub_dialogue/prompts.yml` and returns the parsed dict. Then replace the six
hardcoded extraction prompt string constants and the four inline system message
literals with values derived from this function.

**Changes to `address.py`:**

1. Add `load_prompts()` near the top of the module (after imports):
   - Resolves the YAML path relative to the module file so it works regardless
     of the caller's working directory.
   - Falls back to the current hardcoded defaults (with a `logging.warning`) if
     the file is missing, so the library remains usable in all environments.
   - Accepts an optional `path` argument for test injection.

2. At module level, derive the existing constants from `load_prompts()`:
   ```python
   _PROMPTS = load_prompts()
   EXTRACTION_PROMPT = _PROMPTS["extraction"]["concern"]["A_current"]
   BENEFIT_EXTRACTION_PROMPT = _PROMPTS["extraction"]["benefit"]["A_current"]
   CONCERN_PROMPT_VARIANTS = {
       k: v for k, v in _PROMPTS["extraction"]["concern"].items()
       if k != "default"
   }
   BENEFIT_PROMPT_VARIANTS = {
       k: v for k, v in _PROMPTS["extraction"]["benefit"].items()
       if k != "default"
   }
   ```
   The individual variant constants (`EXTRACTION_PROMPT_B`, `EXTRACTION_PROMPT_C`,
   etc.) can be removed since they are only referenced through the variant dicts.

3. Replace the four system message string literals in `label_cluster`,
   `label_benefit_cluster`, and the framing-lens block with lookups:
   ```python
   _PROMPTS["system_messages"]["qualitative_researcher"]
   _PROMPTS["system_messages"]["engagement_analyst"]
   ```

No public API changes — all existing constant names remain at the same values.

## Acceptance Criteria

- [ ] `load_prompts()` is importable from `pub_dialogue.address`
- [ ] `load_prompts()` resolves the YAML path relative to `address.py` (not cwd)
- [ ] `load_prompts(path=<non-existent file>)` logs a warning and returns defaults without raising
- [ ] `EXTRACTION_PROMPT`, `BENEFIT_EXTRACTION_PROMPT` values are unchanged from before this task
- [ ] `CONCERN_PROMPT_VARIANTS` and `BENEFIT_PROMPT_VARIANTS` contain the same three keys as before (`A_current`, `B_paraphrase`, `C_minimal`)
- [ ] The four system message literals in labelling/lens functions are replaced with YAML lookups
- [ ] `EXTRACTION_PROMPT_B`, `EXTRACTION_PROMPT_C`, `BENEFIT_EXTRACTION_PROMPT_B`, `BENEFIT_EXTRACTION_PROMPT_C` module-level constants are removed (they are only used via the variant dicts)
- [ ] All existing `tests/test_address.py` tests pass without modification

## Implementation Notes

Path resolution should use `Path(__file__).parent / "prompts.yml"` so that
the YAML file is found regardless of where Python is invoked from.

The fallback defaults should be the literal text of the current A_current
prompts — copy them into a small `_DEFAULT_PROMPTS` dict defined just above
`load_prompts()`. This dict is also the reference for the "missing file"
warning message.

`PyYAML` is already available in the project environment (used by VibeSafe
tooling). Confirm it is in `requirements.txt` or equivalent before merging.

## Related

- CIP: 0012
- PRs:
- Documentation:

## Progress Updates

### 2026-05-14

Task created following acceptance of CIP-0012.
