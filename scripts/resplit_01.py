"""
scripts/resplit_01.py — Split 01_processing.ipynb into two notebooks:

  01_processing.ipynb  — chunking + LLM extraction + embedding (both tracks)
                         Run once per corpus; writes raw artifacts.
  01a_clustering.ipynb — clustering + labelling + lens mapping + sensitivity
                         Can re-run without re-extracting or re-embedding.

Usage
-----
    python scripts/resplit_01.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

SRC  = Path("01_processing.ipynb")
OUT1 = Path("01_processing.ipynb")        # overwrites in-place
OUT2 = Path("01a_clustering.ipynb")

# ---------------------------------------------------------------------------
# Cell indices in the CURRENT 01_processing.ipynb
# (0-based; verify with: python scripts/resplit_01.py --list)
# ---------------------------------------------------------------------------
#
# [0-7]   Shared setup: install, imports, config, mkdir, dialogue_utils, API key
# [8]     Section 1 separator
# [9-13]  Ingest: PDF upload, metadata, chunking, quality checks
# [14]    Section 2 separator
# [15-17] Concern extraction (LLM)
# [18]    Section 3 separator
# [19]    Concern embedding
#                    ← split ─────────────────────────────────────────────────
# [20-22] Concern clustering + entropy helpers
# [23]    Section 4 separator
# [24-25] Concern exemplars + LLM labelling
# [26]    Section 5 separator
# [27-30] Concern framing lenses + dendrogram
# [31-33] Benefit extraction (LLM)
# [34]    Section 3B separator
# [35]    Benefit embedding
# [36-38] Benefit clustering + entropy helpers
# [39]    Section 4B separator
# [40-41] Benefit exemplars + LLM labelling
# [42]    Section 5B separator
# [43-44] Benefit framing lenses
# [45-46] Sensitivity analysis (k=60/75/90, concerns + benefits)
# [47]    Artifact manifest

SETUP_CELLS   = list(range(0, 8))          # shared: install → API key
INGEST_CELLS  = list(range(8, 14))         # separators + chunking
CONCERN_EXTRACTION_CELLS = list(range(14, 20))  # separator + LLM + embedding
BENEFIT_EXTRACTION_CELLS = [34] + list(range(31, 34)) + [35]
# ↑ put the Section 3B separator first, then extraction cells, then embedding

CONCERN_CLUSTERING_CELLS = list(range(20, 31))   # clustering → dendrogram
BENEFIT_CLUSTERING_CELLS = list(range(36, 48))   # clustering → manifest

# ---------------------------------------------------------------------------
# Cell templates
# ---------------------------------------------------------------------------

EXTRACTION_CHECKPOINT_SOURCE = """\
# @title Extraction checkpoint — confirm artifacts are saved
# Run this at the end of 01_processing to verify that all raw artifacts
# have been written before starting 01a_clustering.
from pathlib import Path as _Path
_out  = OUTPUT_FOLDER
_ckpt = CHECKPOINT_FOLDER

_EXPECTED = {
    _out  / "paragraph_chunks.csv":     "chunks",
    _out  / "extracted_concerns.csv":   "concern phrases",
    _out  / "extracted_benefits.csv":   "benefit phrases",
    _ckpt / "concern_embeddings.npy":   "concern embeddings",
    _ckpt / "benefit_embeddings.npy":   "benefit embeddings",
}

_ok = True
for _p, _label in _EXPECTED.items():
    _sz = f"{_p.stat().st_size / 1e6:.1f} MB" if _p.exists() else "MISSING"
    _flag = "OK  " if _p.exists() else "MISS"
    print(f"  {_flag}  {_label:<25}  {_sz}")
    if not _p.exists():
        _ok = False

if not _ok:
    raise RuntimeError("Some extraction artifacts are missing — check earlier cells.")
print("\\nAll extraction artifacts present. Run 01a_clustering.ipynb next.")
"""

CLUSTERING_LOADER_SOURCE = """\
# @title Load extraction artifacts
# Loads all outputs written by 01_processing.ipynb so this notebook never
# calls the OpenAI extraction/embedding API or re-processes PDFs.

import json, numpy as np, pandas as pd
from pathlib import Path
from openpyxl import load_workbook  # noqa: F401 (ensures openpyxl available)

chunks_df    = pd.read_csv(OUTPUT_FOLDER / "paragraph_chunks.csv")
concerns_df  = pd.read_csv(OUTPUT_FOLDER / "extracted_concerns.csv")
benefits_df  = pd.read_csv(OUTPUT_FOLDER / "extracted_benefits.csv")

concern_embeddings = np.load(CHECKPOINT_FOLDER / "concern_embeddings.npy")
benefit_embeddings = np.load(CHECKPOINT_FOLDER / "benefit_embeddings.npy")

# Reconstruct concern_ids / benefit_ids if checkpointed
def _load_json(p):
    with open(p) as _f: return json.load(_f)

concern_ids = (
    _load_json(CHECKPOINT_FOLDER / "concern_ids.json")
    if (CHECKPOINT_FOLDER / "concern_ids.json").exists()
    else concerns_df["phrase"].tolist()
)
benefit_ids = (
    _load_json(CHECKPOINT_FOLDER / "benefit_ids.json")
    if (CHECKPOINT_FOLDER / "benefit_ids.json").exists()
    else benefits_df["phrase"].tolist()
)

# Rebuild metadata_lookup needed by benefit merge cell
_meta_candidates = list(OUTPUT_FOLDER.glob("*.xlsx")) + list(Path(".").glob("*.xlsx"))
if _meta_candidates:
    metadata_df = pd.read_excel(_meta_candidates[0])
    metadata_lookup = metadata_df.set_index("filename").to_dict("index")
else:
    metadata_lookup = {}
    print("WARNING: metadata xlsx not found — metadata_lookup is empty")

TECHNOLOGY_CATEGORIES = sorted(chunks_df["technology_meta"].dropna().unique().tolist())

print(f"Chunks:   {len(chunks_df):,}")
print(f"Concerns: {len(concerns_df):,}  |  embeddings: {concern_embeddings.shape}")
print(f"Benefits: {len(benefits_df):,}  |  embeddings: {benefit_embeddings.shape}")
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_code_cell(source: str) -> dict:
    lines = source.rstrip("\n").split("\n")
    lines = [l + "\n" for l in lines]
    lines[-1] = lines[-1].rstrip("\n")
    return {"cell_type": "code", "execution_count": None,
            "metadata": {}, "outputs": [], "source": lines}


def _pick(cells: list[dict], indices: list[int]) -> list[dict]:
    return [copy.deepcopy(cells[i]) for i in indices]


def _nb(kernel_spec, language_info, cells):
    return {"nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": kernel_spec, "language_info": language_info},
            "cells": cells}


def _write(path: Path, nb: dict) -> None:
    with open(path, "w") as f:
        json.dump(nb, f, indent=1)
    print(f"  Wrote {path}  ({len(nb['cells'])} cells)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    import sys
    if "--list" in sys.argv:
        with open(SRC) as f:
            nb = json.load(f)
        for i, cell in enumerate(nb["cells"]):
            src = "".join(cell.get("source", []))
            lines = [l for l in src.strip().split("\n") if l.strip()][:2]
            print(f"[{i:2d}] {'  |  '.join(lines)[:110]}")
        return

    with open(SRC) as f:
        nb = json.load(f)

    cells = nb["cells"]
    ks    = nb.get("metadata", {}).get("kernelspec", {})
    li    = nb.get("metadata", {}).get("language_info", {})

    # --- 01_processing.ipynb (extraction + embedding only) ---
    proc_cells = (
        _pick(cells, SETUP_CELLS)
        + _pick(cells, INGEST_CELLS)
        + _pick(cells, CONCERN_EXTRACTION_CELLS)
        + _pick(cells, BENEFIT_EXTRACTION_CELLS)
        + [_make_code_cell(EXTRACTION_CHECKPOINT_SOURCE)]
    )

    # --- 01a_clustering.ipynb (clustering + labelling + sensitivity) ---
    clust_cells = (
        _pick(cells, SETUP_CELLS)
        + [_make_code_cell(CLUSTERING_LOADER_SOURCE)]
        + _pick(cells, CONCERN_CLUSTERING_CELLS)
        + _pick(cells, BENEFIT_CLUSTERING_CELLS)
    )

    print("Producing notebooks…")
    _write(OUT1, _nb(ks, li, proc_cells))
    _write(OUT2, _nb(ks, li, clust_cells))
    print("\nDone.")
    print(f"  01_processing.ipynb  — setup + ingest + extraction + embedding "
          f"({len(proc_cells)} cells)")
    print(f"  01a_clustering.ipynb — setup + loader + clustering + labelling + "
          f"sensitivity ({len(clust_cells)} cells)")


if __name__ == "__main__":
    main()
