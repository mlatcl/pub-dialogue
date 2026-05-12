---
id: "2026-05-12_add-entropy-saves"
title: "Persist entropy dicts to disk in v19 cells 20 and 58"
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
- artifacts
---

# Task: Persist entropy dicts to disk in v19 cells 20 and 58

## Description

`cluster_entropy`, `cluster_entropy_norm`, and `cross_cutting_clusters` currently
exist only as in-memory globals. The split requires them to be loadable by analysis
notebooks. Append JSON saves to cells 20 (concern entropy) and 58 (benefit entropy)
of `public_dialogue_analyser_v19.ipynb`.

## Acceptance Criteria

- [ ] Cell 20 appended: writes `outputs/cluster_entropy.json` with keys `raw`, `norm`, `cross_cutting`
- [ ] Cell 58 appended: writes `outputs/benefit_cluster_entropy.json` with same structure
- [ ] Both JSON files use string keys (JSON requirement); `load_artifacts` coerces back to int keys

## Implementation Notes

Append to cell 20 (after `cluster_entropy_norm` dict is built):
```python
with open(OUTPUT_FOLDER / "cluster_entropy.json", "w") as _f:
    json.dump({
        "raw": {str(k): v for k, v in cluster_entropy.items()},
        "norm": {str(k): v for k, v in cluster_entropy_norm.items()},
        "cross_cutting": cross_cutting_clusters,
    }, _f)
```

Append to cell 58 (after `normalized_entropy_benefits` dict is built):
```python
with open(OUTPUT_FOLDER / "benefit_cluster_entropy.json", "w") as _f:
    json.dump({
        "raw": {str(k): v for k, v in benefit_cluster_entropy.items()},
        "norm": {str(k): v for k, v in normalized_entropy_benefits.items()},
        "cross_cutting": cross_cutting_clusters_benefits,
    }, _f)
```

## Related

- CIP: 000A

## Progress Updates

### 2026-05-12

Task created. In Progress — implementing as part of CIP-000A notebook split.
