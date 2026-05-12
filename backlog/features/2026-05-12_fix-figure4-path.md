---
id: "2026-05-12_fix-figure4-path"
title: "Fix Figure 4 cell: wrong traceability CSV filename"
status: "In Progress"
priority: "Medium"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "bugs"
related_cips: ["000A"]
owner: ""
dependencies: []
tags:
- backlog
- notebook-split
- bug
---

# Task: Fix Figure 4 cell: wrong traceability CSV filename

## Description

Cell 99 of `public_dialogue_analyser_v19.ipynb` (Figure 4 paper asset) reads
`concern_traceability_paragraphs.csv` but the file actually written to `outputs/`
is named `traceability_paragraphs.csv`. This is a pre-existing naming mismatch
that would cause Figure 4 to fail with a FileNotFoundError.

## Acceptance Criteria

- [ ] Cell 99 `pd.read_csv` changed from `concern_traceability_paragraphs.csv` to `traceability_paragraphs.csv`
- [ ] No other cells affected

## Implementation Notes

Single line change in cell 99 (0-based index). The file `traceability_paragraphs.csv`
already exists in `outputs/`.

## Related

- CIP: 000A

## Progress Updates

### 2026-05-12

Task created. In Progress — implementing as part of CIP-000A notebook split.
