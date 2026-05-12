---
id: "access-assess-address"
title: "Separate Access, Assess, and Address as distinct pipeline stages"
status: "Active"
created: "2026-05-12"
last_reviewed: "2026-05-12"
review_frequency: "Annual"
conflicts_with: []
tags:
- tenet
- pipeline
- data-science
- reproducibility
---

# Project Tenet: Separate Access, Assess, and Address

## Tenet

**Description**: Data science pipelines have three logically distinct stages that must be kept separate: *access*, *assess*, and *address*. Access brings data into digital form — loading files, reading metadata, extracting text. Assess characterises the data in a question-agnostic way: understanding quality, structure, and coverage through work that any researcher could reuse regardless of their research question. Address applies analysis to answer a specific question — invoking LLMs, generating embeddings, clustering phrases.

The critical insight is that assessment work should be done *without* the research question in mind. This keeps assess outputs reusable: a researcher with a different question about the same corpus of public dialogue documents should be able to run the assess stage and get useful, unbiased characterisation of the data. When assess and address are conflated, the diagnostic work becomes entangled with question-specific choices (e.g., which technology terms to filter, which LLM prompt to use), making it harder to reuse and harder to audit.

**Quote**: *"Assess is only work you can do without the question in mind."*

**Examples**:
- Chunk extraction from PDFs belongs in *access* — it is purely about getting text into a usable form, independent of any question
- Quality heuristics that flag likely bibliography sections or table rows belong in *assess* — they characterise data structure without caring whether we are studying concerns, benefits, or something else
- LLM-based concern/benefit extraction belongs in *address* — it is question-specific (the prompt encodes what we are looking for)
- Embedding generation for extracted phrases belongs in *address* — it operates on address-stage outputs
- A corpus word-count distribution or chunk-length histogram belongs in *assess* — informative about the data regardless of downstream question

**Counter-examples**:
- Running quality diagnostics inside the same cell as LLM extraction makes it impossible to reuse the diagnostics without triggering API costs
- Saving chunk quality flags to a checkpoint folder that is only populated after the full pipeline has run prevents question-agnostic reuse
- Mixing metadata joins (access) with technology-term filtering (address) in the same function obscures which stage owns what logic
- A single monolithic processing notebook that must be run top-to-bottom to get any artefacts conflates all three stages

**Conflicts**:
- **Simplicity vs separation**: Keeping three separate modules adds some structural overhead compared to a single `utils.py`. Resolution: the boundary is drawn at the natural seams of the pipeline (before/after LLM invocation), so the cost is low and the reusability gain is high. Shared helpers (path resolution, logging) stay in `utils.py`.
- **Speed of initial development**: During rapid prototyping it can be convenient to write everything in one notebook. Resolution: accept this during exploration, but enforce the separation before code enters the package — the CIP targets the `pub_dialogue` package, not scratch notebooks.
