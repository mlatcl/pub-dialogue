---
author: "neil"
created: "2026-05-12"
last_updated: "2026-05-12"
status: "Proposed"
related_requirements: []
related_cips: ["0003", "000A"]
tags:
  - packaging
  - dialogue-utils
  - reproducibility
compressed: false
---

# CIP-000B: Package pub_dialogue — installable package replacing dialogue_utils.py

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [ ] In Progress - Implementation underway
- [ ] Implemented - Code changes complete
- [ ] Closed - Implementation reviewed and merged

## Summary

Replace the top-level `dialogue_utils.py` module with a proper Python package
`pub_dialogue`, pip-installable directly from the GitHub repository.  The
notebook install cell shrinks to a single `pip install` and the `sys.path`
hack disappears entirely.  All shared helpers are accessed as
`pub_dialogue.utils` (imported as `du` by convention).

## Motivation

Currently every notebook carries a fragile install cell:

```python
!pip install -q PyMuPDF openai scikit-learn ...   # long list, easy to drift
import sys, os
sys.path.insert(0, ...)                             # path hack
import dialogue_utils as du
```

Problems:
- Dependency list must be kept in sync manually across notebooks
- `sys.path` trick breaks when the notebook is run from a different directory
- There is no canonical way to install the project on a new machine or in Colab
- `dialogue_utils.py` has no version, no metadata, no entry-point

A proper package fixes all of this:

```python
# Colab
!pip install -q git+https://github.com/mlatcl/pub-dialogue.git

# Local (once, in the repo)
pip install -e .

# All notebooks
import pub_dialogue.utils as du
```

## Detailed Description

### Package structure

```
pub-dialogue/               ← repo root (existing name matches)
├── pyproject.toml          ← package metadata, dependencies, build config
├── pub_dialogue/           ← new package directory
│   ├── __init__.py         ← version + convenience re-exports
│   └── utils.py            ← moved from dialogue_utils.py (unchanged content)
├── dialogue_utils.py       ← thin backward-compat shim (one import line)
├── tests/
│   └── test_dialogue_utils.py  ← update import to pub_dialogue.utils
└── ...notebooks...
```

### pyproject.toml

Uses `[project]` table (PEP 621) with `hatchling` as the build backend
(zero-config, no setup.py needed):

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pub-dialogue"
version = "0.1.0"
description = "Public Dialogue Analyser — shared utilities and pipeline notebooks"
requires-python = ">=3.10"
dependencies = [
    "numpy<2",
    "pandas>=2.0",
    "scipy>=1.11",
    "scikit-learn>=1.3",
    "PyMuPDF>=1.23",
    "openai>=1.10",
    "matplotlib>=3.8",
    "seaborn>=0.13",
    "plotly>=5.18",
    "tqdm>=4.66",
    "openpyxl>=3.1",
    "ipykernel>=6.28",
]
```

### Backward compatibility shim

`dialogue_utils.py` becomes a one-liner so any code that already imports it
continues to work without change:

```python
# dialogue_utils.py — backward-compat shim; use pub_dialogue.utils instead
from pub_dialogue.utils import *  # noqa: F401, F403
```

### Notebook install cell (all notebooks)

```python
# @title Install / verify pub-dialogue package
try:
    import pub_dialogue
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
        "git+https://github.com/mlatcl/pub-dialogue.git"])
    import pub_dialogue
```

### Import convention (all notebooks)

```python
import pub_dialogue.utils as du
```

The existing `import dialogue_utils as du` continues to work via the shim,
so notebooks can be migrated incrementally.

## Implementation Plan

1. Create `pub_dialogue/` directory with `__init__.py` and `utils.py`
   (move content of `dialogue_utils.py` verbatim)
2. Create `pyproject.toml`
3. Replace `dialogue_utils.py` with the backward-compat shim
4. Update `tests/test_dialogue_utils.py` to import from `pub_dialogue.utils`
5. Update install cell in `01_processing.ipynb` and `01a_clustering.ipynb`
6. Update import lines in all split notebooks (00–05) from `dialogue_utils` to `pub_dialogue.utils`
7. Verify `pip install -e .` works locally; confirm tests pass
8. Commit

## Backward Compatibility

- `dialogue_utils.py` shim preserves all existing `import dialogue_utils as du` usage
- Notebooks can be migrated to `pub_dialogue.utils` incrementally
- No change to public API of any function

## Testing Strategy

- Run `pytest tests/ -v` after moving content; all existing tests must pass
- Verify `pip install -e .` installs correctly and `import pub_dialogue.utils` succeeds
- Verify the backward-compat shim works: `import dialogue_utils; dialogue_utils.normalized_entropy`

## Related Requirements

- Extends CIP-0003 (extracting dialogue_utils) by making it a proper package
- Enables CIP-000A analysis notebooks to install cleanly on Colab

## Implementation Status

- [ ] Create pub_dialogue/ package directory
- [ ] Create pyproject.toml
- [ ] Replace dialogue_utils.py with backward-compat shim
- [ ] Update test imports
- [ ] Update notebook install cells
- [ ] Update notebook import lines
- [ ] Verify pip install -e . and tests pass

## References

- [PEP 621 — project metadata](https://peps.python.org/pep-0621/)
- [Hatchling build backend](https://hatch.pypa.io/latest/config/build/)
- CIP-0003: Extracting dialogue_utils
- CIP-000A: Notebook split
