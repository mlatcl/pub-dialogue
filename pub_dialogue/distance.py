"""
pub_dialogue.distance — Document-level distance analysis (EMD + MDS + PERMANOVA).

Tests whether documents from different technology groups (e.g. AI / Data /
Other) differ in *what they are concerned about*, without using the LLM
framing lenses, the σ² mixture weights or the cross-cutting threshold.

Pipeline:
  1. Each document → a distribution over the K clusters
     (share of its phrases in each cluster).
  2. Ground cost between clusters = cosine distance between centroids, so
     moving mass between semantically close clusters is cheap.
  3. Earth Mover's Distance (Wasserstein-1) between every pair of documents.
  4. Classical (Torgerson) MDS of the distance matrix for a 2-D map.
  5. PERMANOVA (Anderson 2001) — do group centroids differ? — with
     PERMDISP (Anderson 2006) as a check that a PERMANOVA result is not just
     a difference in within-group spread.

Requires POT (``pip install pot``), already installed by 01a_clustering.

Public API:
  document_cluster_distributions, cosine_ground_cost, emd_distance_matrix,
  classical_mds, permanova, permdisp, pairwise_permanova, axis_correlates,
  run_document_distance_analysis
"""

from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. Document × cluster distributions
# ---------------------------------------------------------------------------

def document_cluster_distributions(
    phrases_df: pd.DataFrame,
    n_clusters: int,
    doc_col: str = "source_file",
    cluster_col: str = "cluster_id",
    min_phrases: int = 50,
) -> Tuple[np.ndarray, List[str], pd.Series]:
    """Share of each document's phrases falling in each cluster.

    Documents with fewer than *min_phrases* phrases are dropped (their
    distributions are too noisy to place reliably).

    Returns
    -------
    P : (n_docs, n_clusters) array, rows sum to 1
    docs : list of document names (row order of P)
    n_phrases : phrase count per kept document (same order)
    """
    counts = (phrases_df.groupby([doc_col, cluster_col]).size()
              .unstack(fill_value=0)
              .reindex(columns=range(n_clusters), fill_value=0))
    totals = counts.sum(axis=1)
    counts = counts[totals >= min_phrases]
    totals = totals[totals >= min_phrases]
    P = counts.to_numpy(dtype=float) / totals.to_numpy(dtype=float)[:, None]
    return P, counts.index.tolist(), totals


# ---------------------------------------------------------------------------
# 2–3. Ground cost and EMD
# ---------------------------------------------------------------------------

def cosine_ground_cost(centroids: np.ndarray) -> np.ndarray:
    """Cosine distance between cluster centroids (K × K, zero diagonal)."""
    C = np.asarray(centroids, dtype=float)
    C = C / np.linalg.norm(C, axis=1, keepdims=True)
    M = 1.0 - C @ C.T
    np.fill_diagonal(M, 0.0)
    return np.clip(M, 0.0, None)


def emd_distance_matrix(P: np.ndarray, M: np.ndarray) -> np.ndarray:
    """Pairwise Earth Mover's Distance between the rows of *P* under cost *M*."""
    try:
        import ot  # Python Optimal Transport
    except ImportError as exc:
        raise ImportError("POT is required: pip install pot") from exc
    M = np.ascontiguousarray(M, dtype=np.float64)
    n = P.shape[0]
    D = np.zeros((n, n))
    for i in range(n):
        a = np.ascontiguousarray(P[i], dtype=np.float64)
        for j in range(i + 1, n):
            b = np.ascontiguousarray(P[j], dtype=np.float64)
            D[i, j] = D[j, i] = ot.emd2(a, b, M)
    return D


# ---------------------------------------------------------------------------
# 4. Classical MDS
# ---------------------------------------------------------------------------

def classical_mds(D: np.ndarray, n_components: int = 2) -> Dict[str, object]:
    """Classical (Torgerson) MDS / principal coordinates analysis.

    Returns a dict with:
      coords        (n, n_components) coordinates
      eigenvalues   all eigenvalues, descending
      explained     share of the positive-eigenvalue total per kept axis
      negative_ratio  |sum of negative eigenvalues| / sum of positive ones —
                    how far D is from being exactly representable in
                    Euclidean space (0 = perfectly; small = little distortion)
      full_coords   coordinates on all positive axes (used by PERMDISP)
    """
    n = D.shape[0]
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    order = np.argsort(w)[::-1]
    w, V = w[order], V[:, order]
    pos = w > 1e-12
    pos_sum = w[pos].sum()
    full = V[:, pos] * np.sqrt(w[pos])
    return {
        "coords": full[:, :n_components],
        "eigenvalues": w,
        "explained": w[:n_components] / pos_sum,
        "negative_ratio": float(-w[w < -1e-12].sum() / pos_sum),
        "full_coords": full,
    }


# ---------------------------------------------------------------------------
# 5. PERMANOVA and PERMDISP
# ---------------------------------------------------------------------------

def _pseudo_f(D2: np.ndarray, groups: np.ndarray) -> Tuple[float, float]:
    """Pseudo-F and R² from a squared distance matrix (Anderson 2001)."""
    n = len(groups)
    labels = np.unique(groups)
    a = len(labels)
    iu = np.triu_indices(n, 1)
    ss_total = D2[iu].sum() / n
    ss_within = 0.0
    for g in labels:
        idx = np.where(groups == g)[0]
        if len(idx) > 1:
            sub = D2[np.ix_(idx, idx)]
            ss_within += sub[np.triu_indices(len(idx), 1)].sum() / len(idx)
    ss_between = ss_total - ss_within
    f = (ss_between / (a - 1)) / (ss_within / (n - a))
    return f, ss_between / ss_total


def permanova(D: np.ndarray, groups: Sequence, n_perm: int = 9999,
              seed: int = 42) -> Dict[str, float]:
    """One-way PERMANOVA on distance matrix *D*.

    R² = share of total (squared-distance) variation explained by group.
    p  = permutation p-value, (1 + #{F_perm ≥ F_obs}) / (1 + n_perm).
    """
    groups = np.asarray(groups)
    D2 = np.asarray(D) ** 2
    f_obs, r2 = _pseudo_f(D2, groups)
    rng = np.random.default_rng(seed)
    exceed = sum(_pseudo_f(D2, rng.permutation(groups))[0] >= f_obs
                 for _ in range(n_perm))
    return {"pseudo_F": f_obs, "R2": r2, "p_value": (1 + exceed) / (1 + n_perm),
            "n_docs": len(groups), "n_groups": len(np.unique(groups))}


def permdisp(D: np.ndarray, groups: Sequence, n_perm: int = 9999,
             seed: int = 42) -> Dict[str, object]:
    """Test whether groups differ in spread (multivariate dispersion).

    Distances from each document to its group centroid in principal-
    coordinate space, compared across groups by ANOVA F with a permutation
    p-value.  A significant PERMANOVA with a non-significant PERMDISP means
    groups differ in *location*, not just spread.
    """
    groups = np.asarray(groups)
    X = classical_mds(np.asarray(D))["full_coords"]
    labels = np.unique(groups)
    z = np.zeros(len(groups))
    for g in labels:
        idx = groups == g
        z[idx] = np.linalg.norm(X[idx] - X[idx].mean(axis=0), axis=1)

    def _anova_f(values, grp):
        grand = values.mean()
        ssb = sum((grp == g).sum() * (values[grp == g].mean() - grand) ** 2 for g in labels)
        ssw = sum(((values[grp == g] - values[grp == g].mean()) ** 2).sum() for g in labels)
        return (ssb / (len(labels) - 1)) / (ssw / (len(values) - len(labels)))

    f_obs = _anova_f(z, groups)
    rng = np.random.default_rng(seed)
    exceed = sum(_anova_f(z, rng.permutation(groups)) >= f_obs for _ in range(n_perm))
    return {"F": f_obs, "p_value": (1 + exceed) / (1 + n_perm),
            "mean_distance_to_centroid": {g: float(z[groups == g].mean()) for g in labels}}


def pairwise_permanova(D: np.ndarray, groups: Sequence, n_perm: int = 9999,
                       seed: int = 42) -> pd.DataFrame:
    """PERMANOVA and PERMDISP for every pair of groups.

    Bonferroni-adjusted p-values are included for both.  Read each row as:
    a significant PERMANOVA with a NON-significant PERMDISP is a clean
    difference in location (what documents are concerned about); if PERMDISP
    is also significant, part of the PERMANOVA result reflects one group
    being more tightly clustered than the other.  ``spread_first`` and
    ``spread_second`` are the mean distances to centroid of the two groups
    in the order they are named in ``comparison``.
    """
    groups = np.asarray(groups)
    labels = list(np.unique(groups))
    pairs = list(combinations(labels, 2))
    rows = []
    for g1, g2 in pairs:
        mask = np.isin(groups, [g1, g2])
        Dm, gm = D[np.ix_(mask, mask)], groups[mask]
        res = permanova(Dm, gm, n_perm, seed)
        disp = permdisp(Dm, gm, n_perm, seed)
        spread = disp["mean_distance_to_centroid"]
        rows.append({"comparison": f"{g1} vs {g2}", **res,
                     "dispersion_F": disp["F"], "dispersion_p": disp["p_value"],
                     "spread_first": spread[g1], "spread_second": spread[g2]})
    out = pd.DataFrame(rows)
    out["p_bonferroni"] = np.minimum(1.0, out["p_value"] * len(pairs))
    out["dispersion_p_bonferroni"] = np.minimum(1.0, out["dispersion_p"] * len(pairs))
    return out


# ---------------------------------------------------------------------------
# Axis interpretation
# ---------------------------------------------------------------------------

def axis_correlates(coords: np.ndarray, P: np.ndarray,
                    cluster_names: Dict[int, str], top: int = 5) -> pd.DataFrame:
    """For each MDS axis, the clusters whose document shares correlate most
    negatively and positively with position on that axis."""
    rows = []
    for a in range(coords.shape[1]):
        r = np.array([np.corrcoef(coords[:, a], P[:, k])[0, 1]
                      if P[:, k].std() > 0 else 0.0 for k in range(P.shape[1])])
        order = np.argsort(r)
        for end, idxs in [("negative", order[:top]), ("positive", order[::-1][:top])]:
            for k in idxs:
                rows.append({"axis": a + 1, "end": end, "cluster_id": int(k),
                             "label": cluster_names.get(int(k), f"Cluster {k}"),
                             "r": float(r[k])})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# One-call wrapper
# ---------------------------------------------------------------------------

def run_document_distance_analysis(
    phrases_df: pd.DataFrame,
    centroids: np.ndarray,
    doc_group: Dict[str, str],
    cluster_names: Optional[Dict[int, str]] = None,
    min_phrases: int = 50,
    n_perm: int = 9999,
    seed: int = 42,
) -> Dict[str, object]:
    """Run the full EMD → MDS → PERMANOVA/PERMDISP analysis.

    Parameters
    ----------
    phrases_df : one row per phrase with ``source_file`` and ``cluster_id``.
    centroids  : (K, dim) cluster centroids for the same clustering.
    doc_group  : maps each source_file to its group label (e.g. AI/Data/Other).
    """
    K = centroids.shape[0]
    P, docs, n_phr = document_cluster_distributions(phrases_df, K, min_phrases=min_phrases)
    groups = np.array([doc_group[d] for d in docs])
    M = cosine_ground_cost(centroids)
    D = emd_distance_matrix(P, M)
    mds = classical_mds(D, 2)
    dropped = sorted(set(phrases_df["source_file"]) - set(docs))
    return {
        "docs": docs, "groups": groups, "n_phrases": n_phr.to_numpy(),
        "P": P, "D": D, "mds": mds, "dropped_docs": dropped,
        "permanova": permanova(D, groups, n_perm, seed),
        "pairwise": pairwise_permanova(D, groups, n_perm, seed),
        "permdisp": permdisp(D, groups, n_perm, seed),
        "axes": axis_correlates(mds["coords"], P, cluster_names or {}),
    }
