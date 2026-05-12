---
id: "2026-05-12_cip000d-update-utils-py"
title: "Update pub_dialogue/utils.py with re-exports for access/assess/address"
status: "Proposed"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000D"]
owner: ""
dependencies: [
  "2026-05-12_cip000d-create-access-py",
  "2026-05-12_cip000d-create-assess-py",
  "2026-05-12_cip000d-create-address-py"
]
tags:
- backlog
- cip000d
- access-assess-address
- refactoring
---

# Task: Update pub_dialogue/utils.py with re-exports for access/assess/address

## Description

Once `access.py`, `assess.py`, and `address.py` exist, update
`pub_dialogue/utils.py` to:

1. Remove the bodies of all migrated functions (replaced by imports)
2. Add re-export blocks at the top so all existing `from pub_dialogue.utils
   import ...` calls continue to work unchanged

Re-export blocks to add:

```python
from pub_dialogue.access import (
    extract_chunks_from_pdf, load_artifacts, reset_chunk_stats,
    get_chunk_stats, _split_into_sentences, _repack_sentences_into_chunks,
    _extract_paragraphs_from_blocks, _paragraph_split,
)
from pub_dialogue.assess import (
    validate_extraction_cache, write_extraction_diagnostics,
    filter_missing_source_text, is_privacy_text, entropy_by_year,
    vocabulary_frequency_diagnostic, generate_validation_summary,
    _looks_like_bibliography, _looks_like_table_row,
    plot_data_quality, flag_chunk_quality,
)
from pub_dialogue.address import (
    ExtractionResult, extract_phrases, get_embeddings_batch, label_cluster,
    label_benefit_cluster, ai_fingerprint_over_crosscut, run_sensitivity,
    run_for_k, _volume_table, _top_clusters,
    extract_concerns_from_paragraph, extract_benefits_from_paragraph,
    assign_window,
)
```

Functions that remain in `utils.py` (not migrated):
`show_status`, `show_complete`, `show_warning`, `save_checkpoint`,
`load_checkpoint`, `pretty_label`, `clusters_to_labels`, `clusters_to_lenses`,
`html_escape`, `normalized_entropy`, `hhi`, `topk_share`, `parse_year`,
`tokenize`.

## Acceptance Criteria

- [ ] All migrated function bodies removed from `utils.py`
- [ ] Re-export blocks added; `from pub_dialogue.utils import extract_chunks_from_pdf` still works
- [ ] `from pub_dialogue.utils import ExtractionResult` still works
- [ ] `dialogue_utils.py` shim still works (it imports from utils)
- [ ] Full `pytest tests/ -v` passes after this change

## Implementation Notes

Run `pytest tests/ -v` immediately after this change to confirm backward
compatibility. This is the highest-risk step — the re-export mechanism must
cover every name that existing code or tests import from `utils`.

## Related

- CIP: 000D

## Progress Updates

### 2026-05-12

Task created.
