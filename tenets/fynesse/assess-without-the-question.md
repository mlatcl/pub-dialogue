---
id: "assess-without-the-question"
title: "Assess Without the Question"
status: "Active"
created: "2026-05-13"
last_reviewed: "2026-05-13"
review_frequency: "Annual"
conflicts_with: []
tags:
  - assessment
  - reproducibility
  - data-quality
---

## Tenet: assess-without-the-question

**Title**: Assess Without the Question

**Description**: All work performed in the Assess phase must be independent of the specific analysis question being asked. Assessment is about understanding the data as it is — its structure, quality, encodings, missing values, outliers, and provenance — not about preparing it for a particular model or analysis. This ensures that the assess layer is reusable across multiple analyses and by multiple analysts. Decisions made in assess that are shaped by the downstream question contaminate the data understanding and make it impossible to share or reuse.

**Quote**: *"Understand the data before you ask it a question."*

**Examples**:
- Documenting how missing values are encoded in a dataset (e.g. `-999` as a sentinel) without deciding what to do about them
- Computing summary statistics, visualising distributions, and checking data types as part of assess
- Making the assess layer importable by any analyst working on the same dataset, regardless of their specific question
- Recording that a particular column has 23% missing values and leaving the imputation decision to the address layer

**Counter-examples**:
- Imputing missing values in assess using the mean because the downstream regression model requires complete cases
- Dropping columns in assess because they are not relevant to the specific analysis question
- Normalising feature scales in assess in a way that is specific to a particular ML algorithm
- Filtering rows in assess to match a particular cohort definition that is part of the research question

**Conflicts**:
- Can feel inefficient when an analyst knows exactly what question they are asking and wants to prepare data for it directly
- Resolution: The question-agnostic assess layer is a one-time cost per dataset; it can then be reused by any analysis on that data
- In some domains, cleaning decisions are always question-specific and no universal assess layer exists
- Resolution: Document this explicitly; the assess layer can still record the raw data properties even if downstream cleaning must be question-specific

**Version**: 1.0 (2026-05-13)
