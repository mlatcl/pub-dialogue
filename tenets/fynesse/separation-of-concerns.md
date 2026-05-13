---
id: "separation-of-concerns"
title: "Separation of Access, Assess, and Address"
status: "Active"
created: "2026-05-13"
last_reviewed: "2026-05-13"
review_frequency: "Annual"
conflicts_with: []
tags:
  - architecture
  - design
  - data-science
---

## Tenet: separation-of-concerns

**Title**: Separation of Access, Assess, and Address

**Description**: The three phases of data science work — Access, Assess, and Address — must remain distinct and separated. Access is concerned with obtaining data from its source; Assess is concerned with understanding the nature of that data; Address is concerned with answering a specific question using that data. Each phase has a clear boundary, a distinct purpose, and must not bleed into the others. Code, documentation, and notebooks should make this separation explicit.

**Quote**: *"Three phases, three concerns, two boundaries — the clarity of each protects the integrity of all."*

**Examples**:
- Implementing `access.py`, `assess.py`, and `address.py` as separate Python modules with clear interfaces between them
- An assess function that loads data via the access module and performs quality checks, with no reference to any analysis question
- An address function that receives already-assessed data and applies a statistical model to answer a specific question
- Keeping database connection logic entirely within access, so assess and address are never aware of the data source

**Counter-examples**:
- Writing a single notebook cell that fetches data from an API, cleans it, and fits a model in one block
- An assess function that imputes missing values using a method chosen because it suits the downstream model
- Putting SQL queries inside address.py to fetch additional data needed for a specific analysis
- A config file that mixes data source credentials (access concerns) with model hyperparameters (address concerns)

**Conflicts**:
- Can create apparent friction when a quick exploratory analysis seems easier to write as a single pipeline
- Resolution: Prefer explicit boundaries even in exploration; the cost is low and the reusability of assess work is high
- May feel over-engineered for very simple one-off analyses
- Resolution: Even a short script benefits from the separation, as the assess layer can be shared with future analyses on the same data

**Version**: 1.0 (2026-05-13)
