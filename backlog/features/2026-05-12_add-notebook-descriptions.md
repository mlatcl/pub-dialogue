---
id: "2026-05-12_add-notebook-descriptions"
title: "Add AI-generated prose descriptions to split notebooks"
status: "In Progress"
priority: "Medium"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "documentation"
related_cips: []
owner: ""
dependencies: []
tags:
- backlog
- notebooks
- documentation
- ai-generated
---

# Task: Add AI-generated prose descriptions to split notebooks

## Description

The 7 split notebooks (`00_data_quality.ipynb` through `05_robustness.ipynb`) are
largely missing prose markdown descriptions explaining what each code cell does and
why it matters. Each code cell has a brief `# @title` annotation, but no surrounding
narrative context.

This task implements a script (`scripts/add_notebook_descriptions.py`) that:

1. Reads each target notebook as JSON
2. Identifies code cells that do not already have a preceding markdown cell
3. For each such cell, calls `LLMClient.complete()` with a prompt containing the
   notebook purpose, nearest section heading, cell title, and full cell source
4. Inserts a new markdown cell immediately before the code cell
5. Writes the updated notebook back to disk

Current state (code cells without a preceding markdown description):
- `00_data_quality.ipynb` — 6 code cells, 0 markdown cells
- `01_processing.ipynb` — 22 code cells, 5 markdown (section dividers only)
- `01a_clustering.ipynb` — 28 code cells, 4 markdown
- `02_shared_structure.ipynb` — 17 code cells, 0 markdown cells
- `03_ai_distinctiveness.ipynb` — 17 code cells, 0 markdown cells
- `04_temporal_dynamics.ipynb` — 11 code cells, 0 markdown cells
- `05_robustness.ipynb` — 14 code cells, 2 markdown cells

## Acceptance Criteria

- [ ] `scripts/add_notebook_descriptions.py` exists and is runnable
- [ ] `--dry-run` flag prints descriptions without modifying notebooks
- [ ] `--notebook` flag targets a single notebook
- [ ] `--model` flag allows switching LLM model
- [ ] All 7 split notebooks have a prose markdown cell before every code cell
- [ ] Existing section-divider markdown cells are preserved unchanged
- [ ] Script is idempotent (skips cells that already have a preceding markdown cell)

## Implementation Notes

Uses `pub_dialogue.client.LLMClient` (default `gpt-4o-mini`) for generation.
The prompt includes notebook name, nearest section heading, `# @title` label, and
full cell source. Generated descriptions are 2–3 sentences of prose.

## Related

- Script: `scripts/add_notebook_descriptions.py`

## Progress Updates

### 2026-05-12

Task created. Script implementation in progress.
