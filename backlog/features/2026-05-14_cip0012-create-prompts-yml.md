---
id: "2026-05-14_cip0012-create-prompts-yml"
title: "Create pub_dialogue/prompts.yml with all extraction prompt templates"
status: "Proposed"
priority: "High"
created: "2026-05-14"
last_updated: "2026-05-14"
category: "features"
related_cips: ["0012"]
owner: ""
dependencies: []
tags:
- backlog
- prompts
- yaml
- cip0012
---

# Task: Create pub_dialogue/prompts.yml

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Create `pub_dialogue/prompts.yml` containing the full text of all six extraction
prompt templates and the four system message strings currently hardcoded in
`address.py`. This file is the single source of truth for prompt wording and
should be committed to the repository.

The six extraction prompts to move (with their current Python names):

- `EXTRACTION_PROMPT` → `extraction.concern.A_current`
- `EXTRACTION_PROMPT_B` → `extraction.concern.B_paraphrase`
- `EXTRACTION_PROMPT_C` → `extraction.concern.C_minimal`
- `BENEFIT_EXTRACTION_PROMPT` → `extraction.benefit.A_current`
- `BENEFIT_EXTRACTION_PROMPT_B` → `extraction.benefit.B_paraphrase`
- `BENEFIT_EXTRACTION_PROMPT_C` → `extraction.benefit.C_minimal`

Each prompt block uses a YAML block scalar (`|`) to preserve newlines and
indentation exactly. A `default:` key under each kind records which variant
`extract_phrases()` should use (initially `A_current` for both).

The four system messages to add under `system_messages:`:

- `qualitative_researcher` — used in `label_cluster` and `label_benefit_cluster`
- `engagement_analyst` — used in the framing-lens prompt

## Acceptance Criteria

- [ ] `pub_dialogue/prompts.yml` exists and is valid YAML (`python -c "import yaml; yaml.safe_load(open('pub_dialogue/prompts.yml'))"` exits 0)
- [ ] All six extraction prompt texts match the current hardcoded strings in `address.py` exactly (whitespace included)
- [ ] `extraction.concern.default` and `extraction.benefit.default` are both set to `A_current`
- [ ] All four system message strings are present under `system_messages`
- [ ] File has a short header comment explaining its purpose and the `{text}` placeholder convention

## Implementation Notes

Use YAML block scalars (`|`) for multi-line prompt strings — this preserves
trailing newlines and avoids escape sequences. The `{text}` placeholder at the
end of each extraction prompt must be preserved exactly as-is so `str.format()`
continues to work.

Verify the prompt text by diffing against the current Python constants:

```bash
python - <<'EOF'
from pub_dialogue.address import EXTRACTION_PROMPT
import yaml
prompts = yaml.safe_load(open("pub_dialogue/prompts.yml"))
assert prompts["extraction"]["concern"]["A_current"].rstrip() == EXTRACTION_PROMPT.rstrip()
print("OK")
EOF
```

## Related

- CIP: 0012
- PRs:
- Documentation:

## Progress Updates

### 2026-05-14

Task created following acceptance of CIP-0012.
