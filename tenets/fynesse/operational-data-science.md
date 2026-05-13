---
id: "operational-data-science"
title: "Designed for Operational Data Science"
status: "Active"
created: "2026-05-13"
last_reviewed: "2026-05-13"
review_frequency: "Annual"
conflicts_with: []
tags:
  - operational
  - evolving-data
  - deployment
---

## Tenet: operational-data-science

**Title**: Designed for Operational Data Science

**Description**: The Fynesse framework is designed for the real-world conditions of operational data science, where data is live, evolving, and sometimes messy — not the idealised conditions of a clean benchmark dataset and a fixed research question. Operational contexts include pandemic response, supply chain management, policy analysis, and any setting where decisions must be made from imperfect data under time pressure. In these settings, a clear separation of concerns, repeatable assessment, and ethically grounded access are not luxuries — they are prerequisites for trustworthy analysis. The framework should be lightweight enough to be adopted quickly and robust enough to support ongoing, evolving work.

**Quote**: *"Real data science happens under pressure, with imperfect data, in evolving situations — the framework must be ready for that."*

**Examples**:
- Structuring a pandemic response analysis so that the access layer can be updated as new data streams come online without changing the assess or address layers
- Using the assess layer to track how data quality changes over time in a live data pipeline
- Designing the address layer so that the analysis question can be updated (e.g. shifting from "how many cases?" to "how effective is the intervention?") without rewriting the access and assess layers
- Making the framework installable in minutes so it can be adopted at the start of an urgent project

**Counter-examples**:
- Building a framework that only works well with clean, static, pre-processed benchmark data
- Requiring extensive setup and configuration before any data work can begin
- Designing the access layer in a way that is tightly coupled to a specific data source that may change or disappear
- Assuming that the analysis question is fixed at the start and will not evolve as understanding develops
- Building processes that require significant re-engineering whenever the data source format changes

**Conflicts**:
- Operational pressures can make it tempting to skip the framework structure in favour of speed
- Resolution: The framework is designed to be lightweight; even a quick adoption of the three-module structure provides significant clarity with minimal overhead
- Some data science work is purely research-oriented with no operational component
- Resolution: The framework still provides value in research contexts through reproducibility and shareability; the operational design philosophy does not prevent research use

**Version**: 1.0 (2026-05-13)
