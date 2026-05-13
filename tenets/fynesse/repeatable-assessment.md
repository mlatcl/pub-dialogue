---
id: "repeatable-assessment"
title: "Repeatable and Shareable Assessment"
status: "Active"
created: "2026-05-13"
last_reviewed: "2026-05-13"
review_frequency: "Annual"
conflicts_with: []
tags:
  - reproducibility
  - collaboration
  - assessment
---

## Tenet: repeatable-assessment

**Title**: Repeatable and Shareable Assessment

**Description**: The assess layer should be written so that any analyst working on the same dataset can use it directly, regardless of their specific analysis question. Assessment work is a public good: understanding the structure, quality, and properties of a dataset benefits everyone who works with it, and that work should not need to be repeated. Assess functions should be deterministic, documented, and free of side effects that depend on the analyst's environment or question. Where possible, assess outputs (quality summaries, visualisations, cleaned data structures) should be shareable with collaborators.

**Quote**: *"Do the assessment work once, well, and share it."*

**Examples**:
- Packaging the assess layer as a module that can be imported by multiple notebooks and analysts
- Writing assess functions that produce the same output when run on the same input, with no hidden state
- Documenting in assess what checks were performed and what properties were found, so others can trust the output
- Making an assess module available in a shared repository so that collaborators do not repeat the same data quality work
- Writing tests for assess functions so that data quality checks can be re-run as the data evolves

**Counter-examples**:
- An assess function that writes results to a hardcoded local path that only exists on one machine
- Assessment code that is buried inside a single analysis notebook and never extracted for reuse
- An assess function with parameters that are set to values specific to one analyst's question
- Performing data quality checks interactively in a notebook without recording what was found
- Treating assessment as a private step that does not need to be shared or documented

**Conflicts**:
- Writing shareable, reproducible assessment code takes more effort than quick interactive exploration
- Resolution: The investment pays off when the same dataset is used for a second analysis or by a second analyst; even a simple module is better than nothing
- Some datasets change frequently and repeatable assessment may require versioning strategies
- Resolution: Version the dataset and the assess output together; document the data snapshot date in the assess layer

**Version**: 1.0 (2026-05-13)
