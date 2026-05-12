---
id: "2026-05-12_add-load-artifacts"
title: "Add load_artifacts() to dialogue_utils.py with tests"
status: "In Progress"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000A"]
owner: ""
dependencies: []
tags:
- backlog
- notebook-split
- dialogue-utils
---

# Task: Add load_artifacts() to dialogue_utils.py with tests

## Description

Add a `load_artifacts(output_folder, checkpoint_folder)` function to
`dialogue_utils.py` that loads all pre-computed analysis artifacts from disk
and returns them in a single dict. This function is the foundation that lets
analysis notebooks (02–05) boot from saved files without calling the OpenAI
API or re-running k-means.

The function must load 22 artifact keys covering: DataFrames (chunks, concerns,
benefits, cluster summaries), numpy arrays (embeddings, centroids), JSON dicts
(labels, lens mappings, entropy dicts), and derived lists (cross-cutting cluster
IDs).

## Acceptance Criteria

- [ ] `load_artifacts(output_folder, checkpoint_folder)` added to `dialogue_utils.py`
- [ ] Returns dict with all 22 keys documented in CIP-000A
- [ ] `numpy` import added at top-level of `dialogue_utils.py` if not already present
- [ ] `TestLoadArtifacts` class added to `tests/test_dialogue_utils.py`
- [ ] Tests cover: all keys present, correct types (DataFrame/ndarray/dict/list)
- [ ] Full pytest suite still passes (no regressions)

## Implementation Notes

Place after `load_checkpoint` (~line 235). The entropy JSON files
(`cluster_entropy.json`, `benefit_cluster_entropy.json`) are written by
task `2026-05-12_add-entropy-saves` — `load_artifacts` reads them with
int-key coercion: `{int(k): v for k, v in d["raw"].items()}`.

## Related

- CIP: 000A
- Task: 2026-05-12_add-entropy-saves (must run before load_artifacts can load entropy files)

## Progress Updates

### 2026-05-12

Task created. In Progress — implementing as part of CIP-000A notebook split.
