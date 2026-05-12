"""
scripts/split_notebook.py — Split the monolithic v19 notebook into 6 thematic notebooks.

Reads public_dialogue_analyser_v19.ipynb and extracts specified cell-index
ranges into separate notebooks.  Analysis notebooks (02–05) receive a standard
"load artifacts" opener cell prepended.  01_processing.ipynb receives a
manifest cell appended.  The original v19 notebook is not modified.

Usage
-----
    python scripts/split_notebook.py                        # defaults
    python scripts/split_notebook.py --source path/to/nb   # custom source
    python scripts/split_notebook.py --dest path/to/dir     # custom output dir

Cell ranges are 0-based, inclusive on both ends.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration — edit these to adjust the split boundaries
# ---------------------------------------------------------------------------

# Cell ranges to extract for each notebook (0-based, inclusive).
# Keys are output filenames; values are lists of (start, end) pairs.
SPLITS: dict[str, list[tuple[int, int]]] = {
    "00_data_quality.ipynb":       [(3, 6), (11, 12)],
    "01_processing.ipynb":         [(3, 29), (52, 65), (106, 106), (116, 116)],
    "02_shared_structure.ipynb":   [(28, 29), (31, 33), (48, 49),
                                    (66, 67), (69, 71), (84, 85), (87, 88)],
    "03_ai_distinctiveness.ipynb": [(34, 40), (72, 77), (96, 98)],
    "04_temporal_dynamics.ipynb":  [(42, 46), (79, 82), (99, 99)],
    "05_robustness.ipynb":         [(93, 94), (101, 105), (109, 115), (119, 119)],
}

# Notebooks that need a "load artifacts" opener (all analysis notebooks)
NEEDS_LOADER = {
    "02_shared_structure.ipynb",
    "03_ai_distinctiveness.ipynb",
    "04_temporal_dynamics.ipynb",
    "05_robustness.ipynb",
}

# The processing notebook gets a manifest cell at the end
NEEDS_MANIFEST = "01_processing.ipynb"

# ---------------------------------------------------------------------------
# Cell templates
# ---------------------------------------------------------------------------

LOADER_SOURCE = """\
# @title Load pre-computed artifacts
# Run this cell before any analysis cell.  It loads all outputs written by
# 01_processing.ipynb from disk so this notebook never calls the OpenAI API
# or re-runs k-means.
from pathlib import Path
import dialogue_utils as du

OUTPUT_FOLDER     = Path("outputs")
CHECKPOINT_FOLDER = Path("checkpoints")

a = du.load_artifacts(OUTPUT_FOLDER, CHECKPOINT_FOLDER)

chunks_df    = a["chunks_df"]
concerns_df  = a["concerns_df"]
benefits_df  = a["benefits_df"]

concern_embeddings  = a["concern_embeddings"]
benefit_embeddings  = a["benefit_embeddings"]
concern_centroids   = a["concern_centroids"]
benefit_centroids   = a["benefit_centroids"]

concern_ids          = a["concern_ids"]
benefit_ids          = a["benefit_ids"]
cluster_labels       = a["cluster_labels"]
benefit_cluster_labels = a["benefit_cluster_labels"]
cluster_summary_df   = a["cluster_summary_df"]
benefit_cluster_summary_df = a["benefit_cluster_summary_df"]

framing_lens_mappings         = a["framing_lens_mappings"]
benefit_framing_lens_mappings = a["benefit_framing_lens_mappings"]

cluster_entropy           = a["cluster_entropy"]
cluster_entropy_norm      = a["cluster_entropy_norm"]
cross_cutting_clusters    = a["cross_cutting_clusters"]

benefit_cluster_entropy          = a["benefit_cluster_entropy"]
normalized_entropy_benefits      = a["normalized_entropy_benefits"]
cross_cutting_clusters_benefits  = a["cross_cutting_clusters_benefits"]

# Convenience: CLUSTER_LABELS / BENEFIT_CLUSTER_LABELS dicts used by plots
CLUSTER_LABELS        = {int(k): v for k, v in cluster_labels.items()}
BENEFIT_CLUSTER_LABELS = {int(k): v for k, v in benefit_cluster_labels.items()}

print(f"Artifacts loaded from {OUTPUT_FOLDER} / {CHECKPOINT_FOLDER}")
print(f"  Chunks: {len(chunks_df):,}  |  Concerns: {len(concerns_df):,}  |  Benefits: {len(benefits_df):,}")
"""

MANIFEST_SOURCE = """\
# @title Artifact manifest — verify all expected outputs were written
# This cell asserts that every artifact expected by the analysis notebooks
# exists on disk.  Run it at the end of 01_processing to confirm a complete run.

from pathlib import Path
_out  = OUTPUT_FOLDER
_ckpt = CHECKPOINT_FOLDER

_EXPECTED_OUTPUT = [
    "paragraph_chunks.csv",
    "paragraph_chunks_per_document.csv",
    "extracted_concerns.csv",
    "extracted_benefits.csv",
    "cluster_labels.json",
    "cluster_summary.csv",
    "cluster_exemplars.json",
    "cluster_entropy.json",
    "framing_lens_mappings.json",
    "benefit_cluster_labels.json",
    "benefit_cluster_summary.csv",
    "benefit_cluster_exemplars.json",
    "benefit_cluster_entropy.json",
    "benefit_framing_lens_mappings.json",
]

_EXPECTED_CHECKPOINT = [
    "concern_embeddings.npy",
    "concern_ids.json",
    "cluster_centroids.npy",
    "benefit_embeddings.npy",
    "benefit_ids.json",
    "benefit_cluster_centroids.npy",
]

_missing = []
for _name in _EXPECTED_OUTPUT:
    _p = _out / _name
    if _p.exists():
        print(f"  OK   {_name}")
    else:
        print(f"  MISS {_name}")
        _missing.append(str(_p))

for _name in _EXPECTED_CHECKPOINT:
    _p = _ckpt / _name
    if _p.exists():
        print(f"  OK   checkpoints/{_name}")
    else:
        print(f"  MISS checkpoints/{_name}")
        _missing.append(str(_p))

if _missing:
    raise RuntimeError(
        f"\\n{len(_missing)} artifact(s) missing — check earlier cells:\\n"
        + "\\n".join(f"  {m}" for m in _missing)
    )
print(f"\\nAll {len(_EXPECTED_OUTPUT) + len(_EXPECTED_CHECKPOINT)} artifacts present.")
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_code_cell(source: str) -> dict:
    """Return a minimal Jupyter code cell dict."""
    lines = [line + "\n" for line in source.rstrip("\n").split("\n")]
    lines[-1] = lines[-1].rstrip("\n")
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines,
    }


def _extract_cells(
    all_cells: list[dict],
    ranges: list[tuple[int, int]],
) -> list[dict]:
    """Return deep copies of cells at the given index ranges (inclusive)."""
    result: list[dict] = []
    for start, end in ranges:
        for idx in range(start, end + 1):
            result.append(copy.deepcopy(all_cells[idx]))
    return result


def _build_notebook(
    kernel_spec: dict,
    language_info: dict,
    cells: list[dict],
) -> dict:
    """Assemble a minimal valid .ipynb dict."""
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": kernel_spec,
            "language_info": language_info,
        },
        "cells": cells,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default="public_dialogue_analyser_v19.ipynb",
        help="Path to the source v19 notebook (default: public_dialogue_analyser_v19.ipynb)",
    )
    parser.add_argument(
        "--dest",
        default=".",
        help="Directory to write the produced notebooks (default: repo root)",
    )
    args = parser.parse_args()

    src = Path(args.source)
    dest = Path(args.dest)

    print(f"Reading {src} …")
    with open(src) as f:
        nb = json.load(f)

    all_cells: list[dict] = nb["cells"]
    kernel_spec   = nb.get("metadata", {}).get("kernelspec", {})
    language_info = nb.get("metadata", {}).get("language_info", {})

    print(f"  {len(all_cells)} cells found in source notebook")
    print()

    for name, ranges in SPLITS.items():
        cells = _extract_cells(all_cells, ranges)

        # Prepend loader for analysis notebooks
        if name in NEEDS_LOADER:
            cells = [_make_code_cell(LOADER_SOURCE)] + cells

        # Append manifest for processing notebook
        if name == NEEDS_MANIFEST:
            cells = cells + [_make_code_cell(MANIFEST_SOURCE)]

        out_path = dest / name
        nb_out = _build_notebook(kernel_spec, language_info, cells)
        with open(out_path, "w") as f:
            json.dump(nb_out, f, indent=1)

        n_extracted = sum(end - start + 1 for start, end in ranges)
        print(f"  {name}: {len(cells)} cells "
              f"({n_extracted} extracted, "
              f"{'+ loader' if name in NEEDS_LOADER else ''}"
              f"{'+ manifest' if name == NEEDS_MANIFEST else ''})")

    print(f"\nDone. {len(SPLITS)} notebooks written to {dest.resolve()}")


if __name__ == "__main__":
    main()
