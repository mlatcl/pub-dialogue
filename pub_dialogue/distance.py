"""
pub_dialogue.distance — Document-level distance analysis (EMD + MDS + PERMANOVA).

Thin wrappers around :mod:`multilogue.distance` with pub-dialogue column defaults
(``source_file`` / ``cluster_id``). Requires POT (``pip install pot`` or
``pip install 'multilogue[distance]'``).
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from multilogue.distance import (  # noqa: F401 — re-export public API
    axis_correlates,
    classical_mds,
    cosine_ground_cost,
    emd_distance_matrix,
    pairwise_permanova,
    permanova,
    permdisp,
    run_document_distance_analysis as _run_document_distance_analysis,
)
from multilogue.distance import document_cluster_distributions as _document_cluster_distributions


def document_cluster_distributions(
    phrases_df: pd.DataFrame,
    n_clusters: int,
    doc_col: str = "source_file",
    cluster_col: str = "cluster_id",
    min_phrases: int = 50,
):
    """Share of each document's phrases falling in each cluster."""
    return _document_cluster_distributions(
        phrases_df,
        n_clusters,
        doc_col=doc_col,
        cluster_col=cluster_col,
        min_phrases=min_phrases,
    )


def run_document_distance_analysis(
    phrases_df: pd.DataFrame,
    centroids: np.ndarray,
    doc_group: Dict[str, str],
    cluster_names: Optional[Dict[int, str]] = None,
    min_phrases: int = 50,
    n_perm: int = 9999,
    seed: int = 42,
) -> Dict[str, object]:
    """Full EMD → MDS → PERMANOVA/PERMDISP pipeline (pub-dialogue column names)."""
    return _run_document_distance_analysis(
        phrases_df,
        centroids,
        doc_group,
        cluster_names=cluster_names,
        min_phrases=min_phrases,
        n_perm=n_perm,
        seed=seed,
        doc_col="source_file",
        cluster_col="cluster_id",
    )
