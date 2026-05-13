---
id: "systems-engineering-mindset"
title: "Structured Exploration: Repeatable Outputs from an Iterative Process"
status: "Active"
created: "2026-05-13"
last_reviewed: "2026-05-13"
review_frequency: "Annual"
conflicts_with: []
tags:
  - engineering
  - exploration
  - reproducibility
  - deployment
---

## Tenet: systems-engineering-mindset

**Title**: Structured Exploration: Repeatable Outputs from an Iterative Process

**Description**: Data science is fundamentally exploratory — a spiral of iteration in which understanding of the data, the question, and the method co-evolve. This is not a weakness to be engineered away; it is intrinsic to the discipline. The Fynesse framework does not try to eliminate exploration. Instead it provides structure so that the *outputs* of exploration are repeatable and the *decisions made during* exploration are documented. The distinction between Access, Assess, and Address is a record of where the analyst is in the spiral, not a waterfall of sequential steps. Systems engineering thinking applies not to the process itself but to the artefacts it produces: a deployed pipeline must handle real-world constraints; a shared assess layer must be reproducible; an access function must remain maintainable as data sources evolve.

**Quote**: *"The process is a spiral; the outputs should be a ladder — each rung solid enough to stand on."*

**Examples**:
- Exploring data interactively in a notebook, then distilling the quality checks into a repeatable `assess.data()` function
- Iterating through several modelling approaches in address.py, documenting why earlier approaches were rejected in code comments or a CIP
- Revisiting the access layer as a new data source is discovered during exploration, without invalidating the existing assess work
- Delivering an analysis with documented assumptions so the next analyst (or the same analyst next month) can re-run and extend it
- Asking "how will this be updated when the data changes?" and encoding the answer in the access layer — even if the analysis itself was exploratory

**Counter-examples**:
- Producing a notebook that reaches an interesting conclusion but cannot be re-run by anyone else
- Making cleaning decisions during exploration and leaving them buried in a notebook without extracting them into assess
- Treating the first working model as the final answer without documenting what was tried and why alternatives were rejected
- Building an analysis pipeline that works on a static data snapshot with no plan for refreshing when the data changes
- Optimising model performance on a benchmark without considering whether the model can be deployed under real-world constraints

**Conflicts**:
- Documenting the spiral of exploration takes time that feels at odds with the urgency of getting to an answer
- Resolution: Even brief notes in code comments or a CIP stub preserve enough context to make the work reusable; perfect documentation is the enemy of any documentation
- Some exploration is genuinely throwaway and does not warrant structure
- Resolution: Work that informs a decision or will be shared with others is never truly throwaway; apply the minimum structure that makes it reproducible

**Version**: 1.1 (2026-05-13)
