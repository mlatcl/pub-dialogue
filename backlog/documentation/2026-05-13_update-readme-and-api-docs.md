---
id: "2026-05-13_update-readme-and-api-docs"
title: "Update README and add inline pub_dialogue API reference"
status: "Completed"
priority: "Medium"
created: "2026-05-13"
last_updated: "2026-05-13"
owner: ""
dependencies: []
related_cips: []
tags:
- documentation
- readme
- api
---

# Task: Update README and add inline pub_dialogue API reference

## Description

The README.md is significantly outdated following the CIP-0003–0010 refactoring work.
It still references `dialogue_utils.py` (deleted), the v19 legacy monolith notebook,
and reports 153 tests (now 336). The `pub_dialogue` package, stage classes, and the
new 7-notebook pipeline are not described.

Rewrite the README and add a light inline API reference for the three stage classes.
No Sphinx/docs/ folder needed — this is a research codebase and README-level docs
are appropriate.

## Acceptance Criteria

- [ ] Repository structure table updated to reflect current notebook pipeline and
  `pub_dialogue/` package layout
- [ ] References to `dialogue_utils.py` and legacy v19 monolith removed
- [ ] Quick-start section references `01_processing.ipynb`
- [ ] Test count updated (153 → 336)
- [ ] New `pub_dialogue` API section added with stage class usage example and
  per-module 1–2 sentence descriptions
- [ ] Project management section mentions CIP-0010 completion
- [ ] 15 closed CIPs marked `compressed: true` in their frontmatter

## Implementation Notes

No Python code changes. Pure documentation update.

## Related

- CIP: 0010 (most recent completed CIP)

## Progress Updates

### 2026-05-13
Task created as part of post-CIP-0010 documentation push.

### 2026-05-13 (completion)
README fully rewritten: updated repository structure table, notebook pipeline overview,
removed all references to dialogue_utils.py and v19 monolith, updated test count to 336,
added pub_dialogue API section with stage class usage examples. 15 closed CIPs marked
compressed: true. Backlog task marked Completed.
