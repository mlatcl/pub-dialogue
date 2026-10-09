"""
pub_dialogue.crosscut — Is a concern (or benefit) cluster shared across technologies?

Replaces the raw-count entropy measure.  That measure mostly tracked how much
of a cluster came from AI: AI supplies about half of all phrases, so any
AI-heavy cluster scored "technology-specific" even when it appeared in every
technology, and simply relabelling documents changed the count of
cross-cutting clusters substantially.

Measure — coverage (every technology counts equally)
----------------------------------------------------
For each technology t, s_tk = the share of t's phrases that fall in cluster k.
The cluster's *coverage* is the number of technologies where s_tk is at least
``level`` × the cluster's average share across technologies (default 0.5:
"at least half as prominent as it typically is").

Classification — descriptive
----------------------------
A cluster is **cross-cutting** if its coverage is at least ``min_fraction`` of
the technologies (default 0.5, i.e. 6 of 12), otherwise **concentrated**.
This is a transparent description, not a significance test; report it
alongside :func:`crosscut_sensitivity`, which varies ``level``,
``min_fraction`` and the minimum documents per technology.

Corpus-level test — shuffling technology labels across documents
----------------------------------------------------------------
To ask whether technology structures which concerns are raised at all, the
technology labels are shuffled across documents (keeping each technology's
number of documents) ``n_perm`` times and coverage is recomputed.  If the
observed median coverage sits inside the shuffled distribution, concerns are
no more technology-bound than they are document-bound — the shared-structure
claim.  Per-cluster shuffled p-values (with Benjamini–Hochberg q) are also
reported as diagnostics; with several single-document technologies they have
little power, which is why the classification is descriptive.

Public API:
  technology_shares, coverage_counts, required_coverage,
  classify_crosscutting, crosscut_sensitivity, save_crosscutting,
  plot_stable_core
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

DEFAULT_LEVEL = 0.5
DEFAULT_MIN_FRACTION = 0.5
DEFAULT_N_PERM = 1000


# ---------------------------------------------------------------------------
# Core quantities
# ---------------------------------------------------------------------------

def technology_shares(phrases_df: pd.DataFrame, n_clusters: int,
                      tech_col: str = "technology_meta",
                      cluster_col: str = "cluster_id") -> pd.DataFrame:
    """Technologies × clusters: share of each technology's phrases in each cluster."""
    ct = (pd.crosstab(phrases_df[tech_col], phrases_df[cluster_col])
          .reindex(columns=range(n_clusters), fill_value=0))
    return ct.div(ct.sum(axis=1), axis=0)


def _coverage(shares: np.ndarray, level: float) -> np.ndarray:
    """Number of technologies (rows) at ≥ level × mean share, per cluster (cols)."""
    mean = shares.mean(axis=0, keepdims=True)
    return ((shares >= level * mean) & (shares > 0)).sum(axis=0)


def coverage_counts(shares: pd.DataFrame, level: float = DEFAULT_LEVEL) -> pd.Series:
    """Coverage per cluster from a technologies × clusters share table."""
    return pd.Series(_coverage(shares.to_numpy(dtype=float), level),
                     index=shares.columns, name="coverage")


def required_coverage(n_technologies: int, min_fraction: float = DEFAULT_MIN_FRACTION) -> int:
    """Coverage needed to count as cross-cutting, e.g. 6 of 12 at min_fraction 0.5."""
    return max(1, math.ceil(min_fraction * n_technologies - 1e-9))


def _shares_from_assignment(doc_counts: np.ndarray, tech_codes: np.ndarray,
                            n_techs: int) -> np.ndarray:
    onehot = np.zeros((n_techs, len(tech_codes)))
    onehot[tech_codes, np.arange(len(tech_codes))] = 1.0
    tech_counts = onehot @ doc_counts
    totals = tech_counts.sum(axis=1, keepdims=True)
    return np.divide(tech_counts, totals, out=np.zeros_like(tech_counts), where=totals > 0)


def _bh(p: np.ndarray) -> np.ndarray:
    """Benjamini–Hochberg adjusted p-values."""
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(q, 1.0)
    return out


# ---------------------------------------------------------------------------
# Classification + corpus-level test
# ---------------------------------------------------------------------------

def classify_crosscutting(
    phrases_df: pd.DataFrame,
    n_clusters: int,
    tech_col: str = "technology_meta",
    doc_col: str = "source_file",
    cluster_col: str = "cluster_id",
    level: float = DEFAULT_LEVEL,
    min_fraction: float = DEFAULT_MIN_FRACTION,
    min_docs_per_tech: int = 1,
    n_perm: int = DEFAULT_N_PERM,
    seed: int = 42,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """Classify clusters as cross-cutting / concentrated and run the shuffling test.

    Parameters
    ----------
    level : a technology "covers" a cluster if its share is ≥ level × the
        cluster's mean share across technologies.
    min_fraction : cross-cutting if coverage ≥ min_fraction × technologies.
    min_docs_per_tech : drop technologies with fewer documents (3 = the
        sensitivity check without single-document technologies).
    n_perm : shuffles for the corpus-level test (0 = skip the test).

    Returns
    -------
    clusters : one row per cluster.
    summary  : corpus-level numbers.
    """
    df = phrases_df.dropna(subset=[tech_col, cluster_col])
    if doc_col in df.columns:
        docs_per_tech = df.groupby(tech_col)[doc_col].nunique()
        keep = docs_per_tech[docs_per_tech >= min_docs_per_tech].index
        df = df[df[tech_col].isin(keep)]

    shares_df = technology_shares(df, n_clusters, tech_col, cluster_col)
    techs = list(shares_df.index)
    T = len(techs)
    shares = shares_df.to_numpy(dtype=float)
    obs = _coverage(shares, level)
    need = required_coverage(T, min_fraction)

    mean_share = shares.mean(axis=0)
    top_idx = shares.argmax(axis=0)
    clusters = pd.DataFrame({
        "cluster_id": np.arange(n_clusters),
        "n_phrases": df[cluster_col].value_counts().reindex(range(n_clusters), fill_value=0).to_numpy(),
        "coverage": obs,
        "n_technologies": T,
        "required_coverage": need,
        "cross_cutting": obs >= need,
        "technologies_present": (shares > 0).sum(axis=0),
        "top_technology": [techs[i] for i in top_idx],
        "top_technology_vs_mean": np.divide(shares.max(axis=0), mean_share,
                                            out=np.zeros(n_clusters), where=mean_share > 0),
    })
    if doc_col in df.columns:
        clusters["n_documents"] = (df.groupby(cluster_col)[doc_col].nunique()
                                   .reindex(range(n_clusters), fill_value=0).to_numpy())

    summary: Dict[str, object] = {
        "level": level, "min_fraction": min_fraction,
        "min_docs_per_tech": min_docs_per_tech,
        "technologies": techs, "n_technologies": T, "required_coverage": need,
        "n_clusters": n_clusters,
        "n_cross_cutting": int(clusters["cross_cutting"].sum()),
        "share_cross_cutting": float(clusters["cross_cutting"].mean()),
        "observed_median_coverage": float(np.median(obs)),
        "n_perm": n_perm,
    }

    if n_perm and doc_col in df.columns:
        doc_counts = (df.groupby([doc_col, cluster_col]).size().unstack(fill_value=0)
                      .reindex(columns=range(n_clusters), fill_value=0))
        doc_tech = df.drop_duplicates(doc_col).set_index(doc_col)[tech_col].reindex(doc_counts.index)
        codes = doc_tech.map({t: i for i, t in enumerate(techs)}).to_numpy()
        X = doc_counts.to_numpy(dtype=float)
        rng = np.random.default_rng(seed)
        null = np.empty((n_perm, n_clusters), dtype=int)
        for b in range(n_perm):
            null[b] = _coverage(_shares_from_assignment(X, rng.permutation(codes), T), level)
        p = (1 + (null <= obs).sum(axis=0)) / (1 + n_perm)
        clusters["shuffled_mean_coverage"] = null.mean(axis=0)
        clusters["concentration_p"] = p
        clusters["concentration_q"] = _bh(p)
        null_medians = np.median(null, axis=1)
        null_share_xc = (null >= need).mean(axis=1)
        summary.update({
            "n_documents": int(len(codes)),
            "shuffled_median_coverage_mean": float(null_medians.mean()),
            "shuffled_median_coverage_95": (float(np.percentile(null_medians, 2.5)),
                                            float(np.percentile(null_medians, 97.5))),
            "shuffled_share_cross_cutting_95": (float(np.percentile(null_share_xc, 2.5)),
                                                float(np.percentile(null_share_xc, 97.5))),
            # one-sided: is coverage lower overall than when technology is meaningless?
            "p_coverage_lower_than_shuffled": float(
                (1 + (null_medians <= np.median(obs)).sum()) / (1 + n_perm)),
            "n_clusters_q_below_0.05": int((clusters["concentration_q"] < 0.05).sum()),
        })
    return clusters, summary


def describe_summary(summary: Dict[str, object], kind: str = "concern") -> str:
    """Plain-language summary lines for printing in a notebook."""
    s = summary
    lines = [
        f"{kind.capitalize()} clusters: {s['n_cross_cutting']} of {s['n_clusters']} cross-cutting "
        f"(appear at ≥ {s['level']:g} × their average prominence in at least "
        f"{s['required_coverage']} of {s['n_technologies']} technologies).",
        f"Median coverage: {s['observed_median_coverage']:g} of {s['n_technologies']} technologies.",
    ]
    if "shuffled_median_coverage_95" in s:
        lo, hi = s["shuffled_median_coverage_95"]
        xlo, xhi = s["shuffled_share_cross_cutting_95"]
        lines += [
            f"With technology labels shuffled across documents ({s['n_perm']} times): median coverage "
            f"{lo:g}–{hi:g} (95% range); share cross-cutting {xlo:.0%}–{xhi:.0%}.",
            f"Is observed coverage lower than shuffled? p = {s['p_coverage_lower_than_shuffled']:.3f} "
            f"(large p = technology adds no more structure than document-to-document variation).",
            f"Clusters individually more concentrated than shuffling (BH q < 0.05): "
            f"{s['n_clusters_q_below_0.05']} — low power with single-document technologies; "
            f"diagnostic only.",
        ]
    return "\n".join(lines)


def crosscut_sensitivity(
    phrases_df: pd.DataFrame,
    n_clusters: int,
    levels: Sequence[float] = (0.25, 0.5, 0.75),
    min_fractions: Sequence[float] = (0.4, 0.5, 0.6),
    min_docs_options: Sequence[int] = (1, 3),
    n_perm: int = 500,
    **kwargs,
) -> pd.DataFrame:
    """Classification and shuffling test across settings; one row per setting."""
    rows = []
    for md in min_docs_options:
        for lv in levels:
            for mf in min_fractions:
                _, s = classify_crosscutting(phrases_df, n_clusters, level=lv, min_fraction=mf,
                                             min_docs_per_tech=md, n_perm=n_perm, **kwargs)
                row = {
                    "min_docs_per_tech": md, "level": lv, "min_fraction": mf,
                    "technologies": s["n_technologies"],
                    "required": f"{s['required_coverage']} of {s['n_technologies']}",
                    "cross_cutting": s["n_cross_cutting"],
                    "share_cross_cutting": round(s["share_cross_cutting"], 3),
                    "median_coverage": s["observed_median_coverage"],
                }
                if "shuffled_median_coverage_95" in s:
                    lo, hi = s["shuffled_median_coverage_95"]
                    row["shuffled_median_95"] = f"{lo:g}–{hi:g}"
                    row["p_lower_than_shuffled"] = round(s["p_coverage_lower_than_shuffled"], 3)
                rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_crosscutting(clusters: pd.DataFrame, summary: Dict[str, object],
                      output_folder, kind: str = "concern",
                      entropy_raw: Optional[Dict] = None,
                      entropy_norm: Optional[Dict] = None) -> None:
    """Write the classification where downstream notebooks look for it.

    * ``cluster_entropy.json`` / ``benefit_cluster_entropy.json`` — the
      ``cross_cutting`` list now comes from coverage; ``raw`` and ``norm``
      entropy are kept for reference.  load_artifacts() reads this file.
    * ``cluster_crosscutting_{kind}.csv`` — the per-cluster table.
    """
    output_folder = Path(output_folder)
    name = "cluster_entropy.json" if kind == "concern" else "benefit_cluster_entropy.json"
    payload = {
        "raw": {str(k): float(v) for k, v in (entropy_raw or {}).items()},
        "norm": {str(k): float(v) for k, v in (entropy_norm or {}).items()},
        "cross_cutting": [int(c) for c in clusters.loc[clusters["cross_cutting"], "cluster_id"]],
        "method": "coverage",
        "settings": {k: summary[k] for k in ("level", "min_fraction", "min_docs_per_tech",
                                             "n_technologies", "required_coverage")},
    }
    (output_folder / name).write_text(json.dumps(payload))
    clusters.to_csv(output_folder / f"cluster_crosscutting_{kind}.csv", index=False)


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def plot_stable_core(clusters: pd.DataFrame, labels: Dict[int, str],
                     title: str, path=None, size_quantile: float = 0.75,
                     n_annotate: int = 20):
    """Coverage (x) vs cluster size (y).  Stable core = cross-cutting clusters
    in the top (1 - size_quantile) by size."""
    import matplotlib.pyplot as plt

    d = clusters[clusters["n_phrases"] > 0].copy()
    T = int(d["n_technologies"].iloc[0])
    need = int(d["required_coverage"].iloc[0])
    size_thresh = float(d["n_phrases"].quantile(size_quantile))
    d["core"] = d["cross_cutting"] & (d["n_phrases"] >= size_thresh)
    jitter = np.random.default_rng(0).uniform(-0.18, 0.18, len(d))

    fig, ax = plt.subplots(figsize=(10, 7))
    groups = [(~d["cross_cutting"], f"Concentrated (coverage < {need} of {T})", "#eb6834", 35),
              (d["cross_cutting"] & ~d["core"], "Cross-cutting", "#2a78d6", 40),
              (d["core"], "Stable core (cross-cutting + top 25% by size)", "#0d366b", 80)]
    for mask, lab, col, s in groups:
        m = mask.to_numpy()
        ax.scatter(d.loc[mask, "coverage"] + jitter[m], d.loc[mask, "n_phrases"],
                   s=s, c=col, alpha=0.85, edgecolors="white", linewidths=0.8, label=lab)
    ax.axvline(need - 0.5, color="#999", lw=0.8, ls="--")
    ax.axhline(size_thresh, color="#999", lw=0.8, ls="--")
    show = pd.concat([d[d["core"]].nlargest(n_annotate, "n_phrases"),
                      d[~d["cross_cutting"]].nlargest(5, "n_phrases")])
    for _, r in show.iterrows():
        ax.annotate(labels.get(int(r["cluster_id"]), f"Cluster {int(r['cluster_id'])}"),
                    (r["coverage"], r["n_phrases"]), xytext=(6, 3),
                    textcoords="offset points", fontsize=8)
    ax.set_xticks(range(1, T + 1))
    ax.set_xlabel(f"Coverage: technologies (of {T}) where the cluster is at least "
                  f"half as prominent as its average")
    ax.set_ylabel("Cluster size (number of phrases)")
    ax.set_title(title, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    plt.tight_layout()
    if path is not None:
        plt.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.show()
    return fig
