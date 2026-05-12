---
author: "Neil Lawrence"
created: "2026-05-12"
id: "000D"
last_updated: "2026-05-12"
status: "Proposed"
compressed: false
related_requirements: ["0006"]
related_cips: ["000A", "000B", "000C"]
tags:
- cip
- pipeline
- access-assess-address
- architecture
- refactoring
title: "Restructure pub_dialogue package into access/assess/address modules"
---

# CIP-000D: Restructure pub_dialogue package into access/assess/address modules

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented
- [ ] Deferred - Postponed

## Summary

Create three new Python modules within the `pub_dialogue` package — `access.py`, `assess.py`, and `address.py` — corresponding to the three stages of the data science pipeline described by Neil Lawrence (2021). Migrate functions from `utils.py` and the notebooks into these modules. Maintain full backward compatibility through `utils.py` re-exports.

**Which requirements does this CIP address?** See `related_requirements: ["0006"]` — "Assessment work is question-agnostic and independently reusable."

## Motivation

The current `pub_dialogue/utils.py` and `01_processing.ipynb` conflate three logically distinct pipeline stages:

1. **Access** — bringing data into digital form (PDF loading, metadata reading, text chunking)
2. **Assess** — characterising data quality in a question-agnostic, reusable way (corpus statistics, quality flags)
3. **Address** — answering the specific research question (LLM extraction of concerns/benefits, embeddings)

This conflation has concrete costs:

- Running corpus quality diagnostics requires executing LLM extraction cells first, incurring API cost and latency
- A researcher studying the same corpus with a different question cannot reuse the assess stage without also importing question-specific address logic
- The `utils.py` module provides no structural signal about which functions are safe to call before the LLM pipeline and which are not
- CIP-000A's notebook split (into `00_data_quality.ipynb`, `01_processing.ipynb`, etc.) creates the right notebook boundaries, but the underlying Python code has no corresponding structure

The access/assess/address framework (Lawrence, 2021) identifies the *assess* stage as uniquely reusable: it should be possible to do all assess work without the research question in mind. This CIP implements that principle in the package structure.

## Detailed Description

### Three new modules

#### `pub_dialogue/access.py`

Responsible for getting data into digital form. Contains no question-specific logic. Functions here should be callable before any decisions are made about what we are looking for.

**Functions to migrate from `utils.py`:**
- `extract_chunks_from_pdf()` — the core PDF chunking function
- `_extract_paragraphs_from_blocks()` — internal helper for paragraph extraction
- `_paragraph_split()` — internal helper for paragraph boundary detection
- `_split_into_sentences()` — sentence tokenizer for oversized paragraphs
- `_repack_sentences_into_chunks()` — sentence-level repacking logic
- `reset_chunk_stats()` / `get_chunk_stats()` — chunking statistics counters
- `load_artifacts()` — loads all saved artefacts from disk (added in CIP-000A)

**Functions that notebook cells currently define inline (to be moved here):**
- PDF file discovery (currently notebook cell 10)
- Metadata loading from Excel (currently notebook cell 11)
- `metadata_lookup` construction and validation (currently notebook cell 11)

**Design note**: `access.py` has no dependency on OpenAI, litellm, or any LLM client. Its only external dependencies are PyMuPDF (`fitz`), pandas, and pathlib.

---

#### `pub_dialogue/assess.py`

Responsible for question-agnostic data characterisation. Everything here can be run without knowing what we are looking for or invoking any LLM. Output artefacts from this module should be reusable by any researcher studying the same corpus.

**Functions to migrate from `utils.py`:**
- `vocabulary_frequency_diagnostic()` — corpus-wide phrase frequency analysis

**Functions that notebook cells currently define inline (to be moved here):**
- `_looks_like_bibliography()` (currently cell 14) — chunk quality heuristic
- `_looks_like_table_row()` (currently cell 14) — chunk quality heuristic
- Data quality plot generation (currently cell 13) — produces `data_quality_overview.png`
- Chunk quality flagging and CSV export (currently cell 14) — produces `chunk_quality_flagged.csv`

**Design note**: `assess.py` depends on `access.py` (it takes chunks as input) and on matplotlib/seaborn for plots, but has no dependency on OpenAI or any LLM client. The key invariant: if a function needs to know the research question, it belongs in `address.py`, not here.

---

#### `pub_dialogue/address.py`

Responsible for answering the specific research question. Functions here may invoke LLMs, generate embeddings, and apply question-specific filters (e.g., technology term removal).

**Functions to migrate from `utils.py`:**
- `ExtractionResult` dataclass
- `extract_phrases()` — core LLM extraction logic
- `validate_extraction_cache()` — cache integrity check for extraction results
- `write_extraction_diagnostics()` — yield and failure reporting
- `filter_missing_source_text()` — post-extraction data cleaning
- `get_embeddings_batch()` — batched OpenAI embedding generation
- `label_cluster()` / `clusters_to_labels()` / `clusters_to_lenses()` / `pretty_label()` — cluster labelling helpers
- `ai_fingerprint_over_crosscut()` — AI vs non-AI fingerprint analysis
- `run_sensitivity()` — k-sensitivity analysis

**Functions that notebook cells currently define inline (to be moved here):**
- `_record_failure()` / `_phrase_contains_tech_term()` / `extract_concerns_from_paragraph()` (currently cell 16)
- `_record_benefit_failure()` / `_benefit_phrase_contains_tech_term()` / `extract_benefits_from_paragraph()` (currently cell 22)

**Design note**: `address.py` depends on `access.py` (for chunk data) and may optionally depend on `assess.py` (for quality flags to filter on). It requires an LLM client (OpenAI or litellm via CIP-000C). The `EXTRACTION_PROMPT` and `BENEFIT_EXTRACTION_PROMPT` constants live here.

---

#### Remaining in `pub_dialogue/utils.py`

Shared utilities that do not cleanly belong to a single stage:
- `show_status()` / `show_complete()` / `show_warning()` — UI display helpers
- `save_checkpoint()` / `load_checkpoint()` — generic JSON checkpoint I/O
- `normalized_entropy()` / `hhi()` / `topk_share()` — statistical helpers
- `parse_year()` / `tokenize()` / `is_privacy_text()` / `html_escape()` — general utility functions
- `entropy_by_year()` — analysis helper used across notebooks
- `generate_validation_summary()` — multi-stage validation, used in address/robustness context
- `_volume_table()` / `_top_clusters()` / `_chunk_stats()` — internal helpers

`utils.py` is updated to re-export all public symbols from `access.py`, `assess.py`, and `address.py`, so existing `from pub_dialogue.utils import ...` calls continue to work without modification.

---

### Backward compatibility mechanism

Following the pattern already established by `dialogue_utils.py`:

```python
# pub_dialogue/utils.py (additions at top of file)
from pub_dialogue.access import (
    extract_chunks_from_pdf,
    load_artifacts,
    # ... all public access symbols
)
from pub_dialogue.assess import (
    vocabulary_frequency_diagnostic,
    # ... all public assess symbols
)
from pub_dialogue.address import (
    ExtractionResult,
    extract_phrases,
    get_embeddings_batch,
    # ... all public address symbols
)
```

Existing notebooks using `from pub_dialogue.utils import extract_chunks_from_pdf` continue to work. New code can be more specific: `from pub_dialogue.assess import vocabulary_frequency_diagnostic`.

---

### Relationship to CIP-000A

CIP-000A splits the monolithic notebook into six notebooks along thematic lines (`00_data_quality`, `01_processing`, `02_shared_structure`, etc.). This CIP is complementary: it restructures the underlying Python package along functional/stage lines. Together they produce:

- `00_data_quality.ipynb` → calls `pub_dialogue.access` + `pub_dialogue.assess`
- `01_processing.ipynb` → calls `pub_dialogue.access` + `pub_dialogue.address`
- `02–05_*.ipynb` → loads artefacts, calls `pub_dialogue.address` analysis helpers

### Relationship to CIP-000B and CIP-000C

CIP-000B packaged `pub_dialogue` as an installable package. CIP-000C adds litellm support via `pub_dialogue.client`. This CIP adds structural clarity within the package without changing the installation or LLM client interfaces.

## Implementation Plan

1. **Create `pub_dialogue/access.py`**
   - Move chunking functions from `utils.py`: `extract_chunks_from_pdf`, `_extract_paragraphs_from_blocks`, `_paragraph_split`, `_split_into_sentences`, `_repack_sentences_into_chunks`, `reset_chunk_stats`, `get_chunk_stats`
   - Move `load_artifacts` from `utils.py`
   - Keep imports self-contained (PyMuPDF, pandas, pathlib only — no OpenAI)
   - Add `__all__` listing public API

2. **Create `pub_dialogue/assess.py`**
   - Move `vocabulary_frequency_diagnostic` from `utils.py`
   - Move `_looks_like_bibliography` and `_looks_like_table_row` from notebook cell 14
   - Add data quality plot function wrapping notebook cell 13 logic
   - Keep imports self-contained (pandas, matplotlib/seaborn — no OpenAI)
   - Add `__all__` listing public API

3. **Create `pub_dialogue/address.py`**
   - Move `ExtractionResult`, `extract_phrases`, `validate_extraction_cache`, `write_extraction_diagnostics`, `filter_missing_source_text`, `get_embeddings_batch` from `utils.py`
   - Move cluster labelling helpers from `utils.py`
   - Move `ai_fingerprint_over_crosscut`, `run_sensitivity` from `utils.py`
   - Move inline extraction functions from notebook cells 16 and 22
   - Move `EXTRACTION_PROMPT` and `BENEFIT_EXTRACTION_PROMPT` constants here
   - Add `__all__` listing public API

4. **Update `pub_dialogue/utils.py`**
   - Add re-export blocks for all three new modules
   - Remove migrated function bodies (replaced by imports)
   - Ensure `dialogue_utils.py` shim still works (it imports from `utils`, which re-exports everything)

5. **Update `pub_dialogue/__init__.py`**
   - Expose `access`, `assess`, `address` as submodule names if not already

6. **Update notebooks**
   - Replace inline cell definitions with imports from the appropriate module
   - `01_processing.ipynb` cells 10–14 use `pub_dialogue.access` and `pub_dialogue.assess`
   - `01_processing.ipynb` cells 16–25 use `pub_dialogue.address`

7. **Add tests**
   - `tests/test_access.py`: test `extract_chunks_from_pdf` and `load_artifacts`
   - `tests/test_assess.py`: test quality heuristics without any LLM dependency
   - `tests/test_address.py`: extend existing extraction tests; confirm `ExtractionResult` still importable from `pub_dialogue.utils`
   - Confirm `from pub_dialogue.utils import extract_chunks_from_pdf` still works (backward compat test)

8. **Run full test suite** — `pytest tests/ -v`

## Backward Compatibility

- All existing `from pub_dialogue.utils import ...` calls continue to work unchanged (re-export mechanism)
- `dialogue_utils.py` shim (which imports from `utils`) continues to work unchanged
- No changes to the public API signatures of any migrated functions
- Existing checkpoint files and artefacts on disk are unaffected

## Testing Strategy

- **No-LLM constraint**: `tests/test_assess.py` must not import `openai` or `litellm` at module level. This is enforced by checking that `pub_dialogue.assess` can be imported in an environment with no API key set.
- **Backward compatibility**: add a test asserting that `from pub_dialogue.utils import extract_chunks_from_pdf` succeeds and returns the same object as `from pub_dialogue.access import extract_chunks_from_pdf`.
- **Existing suite**: all 162+ existing tests must pass without modification.
- **Manual smoke test**: `import pub_dialogue.assess; help(pub_dialogue.assess)` should display assess-only functions with no address/LLM references.

## Related Requirements

- [REQ-0006: Assessment work is question-agnostic and independently reusable](../requirements/req0006_question-agnostic-assessment.md)

This CIP implements REQ-0006 by creating `assess.py` as a module with no LLM dependency, making the assess stage independently runnable and reusable.

## Implementation Status

- [ ] Create `pub_dialogue/access.py` and migrate chunking functions
- [ ] Create `pub_dialogue/assess.py` and migrate quality heuristics / diagnostic plot function
- [ ] Create `pub_dialogue/address.py` and migrate extraction, embedding, and clustering helpers
- [ ] Update `pub_dialogue/utils.py` with re-export blocks
- [ ] Update `pub_dialogue/__init__.py`
- [ ] Update notebooks to use module imports
- [ ] Add `tests/test_access.py`, `tests/test_assess.py`, `tests/test_address.py`
- [ ] Run full test suite

## References

- Lawrence, N.D. (2021). ["Access, Assess and Address: A Pipeline for (Automated?) Data Science"](https://inverseprobability.com/talks/notes/access-assess-address-a-pipeline-for-automated-data-science.html). ECML Workshop on Automating Data Science.
- [REQ-0006](../requirements/req0006_question-agnostic-assessment.md) — requirement this CIP implements
- [Tenet: access-assess-address](../tenets/pub-dialogue/access-assess-address.md) — foundational principle
- [CIP-000A](cip000A.md) — notebook split; complementary structural change
- [CIP-000B](cip000B.md) — package installation; this CIP adds structure within the package
- [CIP-000C](cip000C.md) — litellm client; `address.py` will use `pub_dialogue.client`
- `pub_dialogue/utils.py` — source of functions to be migrated
