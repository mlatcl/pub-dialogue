"""Multiverse analysis for the public dialogue paper.

Produces the Cartesian product of defensible analytical choices and
evaluates each configuration against the three headline findings
(R1 shared structure; R2 AI distinctiveness; R3 temporal stability).

Dimensions (cheap — no additional LLM calls, reuse existing artifacts):
  - lens_run_idx : 1..N (reuses ``outputs/framing_lens_mappings_run_*.json``)
  - sigma2_rule  : alternative selection rules on the stability curve
  - baseline     : tech-weighted vs doc-weighted non-AI baseline (R2 only)
  - threshold    : cross-cutting entropy threshold (R1 only)

Dimensions (expensive — require re-runs of 01/01a at different settings):
  - k      : 60, 75, 90 (feed from M6d sensitivity outputs)
  - prompt : V0, V1, V3 (feed from M6b sensitivity outputs)

The expensive dimensions are supported via the ``load_pipeline_artifacts``
hook: supply a loader function that returns the right (centroids,
mappings, concerns_df, cluster_entropy, n_techs) tuple for each (k, prompt)
pair. The baseline loader at k=75, prompt=V0 is provided; others are
``NotImplementedError`` stubs for Jessica to wire up once the expensive
outputs are organised on disk.

Evaluation functions (ℓ):
  - ell_R1 : fraction of concern clusters that are cross-cutting
  - ell_R2 : AI-vs-non-AI pp difference on the top-AI-salient lens
  - ell_R3 : standard deviation of normalised AI concern entropy across
             four time windows (smaller = more "stable spread")

No knowledge of specific lens names, cluster labels, or paper findings
is baked into this module.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy.stats import entropy as scipy_entropy


# =============================================================================
# Configuration dataclass
# =============================================================================


@dataclass(frozen=True)
class MultiverseConfig:
    """One point in the multiverse — a choice for each analytical dimension."""

    k: int = 75
    prompt: str = "V0"
    lens_run_idx: int = 1
    sigma2_rule: str = "min_emd"
    baseline: str = "tech_weighted"
    threshold: float = 0.5

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# =============================================================================
# Enumeration
# =============================================================================


def enumerate_configurations(dimensions: dict[str, list]) -> list[MultiverseConfig]:
    """Build the full Cartesian product of a dimensions dict.

    Parameters
    ----------
    dimensions:
        Dict mapping dimension name (must be a field of :class:`MultiverseConfig`)
        to a list of defensible values. Any field not present uses the
        dataclass default.

    Returns
    -------
    List of :class:`MultiverseConfig` — one per Cartesian combination.
    """
    keys = list(dimensions.keys())
    value_lists = [dimensions[k] for k in keys]
    configs: list[MultiverseConfig] = []
    for combo in itertools.product(*value_lists):
        kwargs = dict(zip(keys, combo))
        configs.append(MultiverseConfig(**kwargs))
    return configs


# =============================================================================
# σ² selection rules
# =============================================================================


def select_sigma2_min_emd(stability_curve: pd.DataFrame) -> float:
    """Pick σ² at the row with minimum mean EMD."""
    idx = stability_curve["mean_emd"].idxmin()
    return float(stability_curve.loc[idx, "sigma2"])


def select_sigma2_min_emd_support_cap(
    stability_curve: pd.DataFrame, support_cap: float = 2.0
) -> float:
    """Pick σ² at the min-EMD row subject to effective-support ≥ ``support_cap``.

    If no row satisfies the constraint, falls back to pure min-EMD.
    """
    if "mean_eff_support" not in stability_curve.columns:
        return select_sigma2_min_emd(stability_curve)
    constrained = stability_curve[stability_curve["mean_eff_support"] >= support_cap]
    if constrained.empty:
        return select_sigma2_min_emd(stability_curve)
    idx = constrained["mean_emd"].idxmin()
    return float(constrained.loc[idx, "sigma2"])


def select_sigma2_median(stability_curve: pd.DataFrame) -> float:
    """Median σ² value in the stability curve — a weak alternative baseline."""
    return float(stability_curve["sigma2"].median())


SIGMA2_RULES: dict[str, Callable[[pd.DataFrame], float]] = {
    "min_emd": select_sigma2_min_emd,
    "min_emd_support_cap": select_sigma2_min_emd_support_cap,
    "median": select_sigma2_median,
}


# =============================================================================
# Soft-weight helpers
# =============================================================================


def _phrase_weights(
    phrases_df: pd.DataFrame,
    mixture_weights: np.ndarray,
    cluster_id_col: str = "cluster_id",
) -> tuple[np.ndarray, np.ndarray]:
    """Return per-phrase soft weights and the mask of rows used."""
    valid = (phrases_df[cluster_id_col] >= 0) & (
        phrases_df[cluster_id_col] < mixture_weights.shape[0]
    )
    cids = phrases_df.loc[valid, cluster_id_col].to_numpy(dtype=int)
    return mixture_weights[cids], valid.to_numpy()


def compute_ai_vs_nonai_pp(
    phrases_df: pd.DataFrame,
    mixture_weights: np.ndarray,
    tech_col: str = "technology_meta",
    baseline: str = "tech_weighted",
) -> np.ndarray:
    """Return per-lens AI vs non-AI pp difference under the chosen baseline.

    Parameters
    ----------
    phrases_df:
        Must have ``cluster_id`` and ``tech_col``.
    mixture_weights:
        (n_clusters, n_lenses) soft-affinity matrix.
    baseline:
        Either ``"tech_weighted"`` (each non-AI technology contributes
        equally) or ``"doc_weighted"`` (non-AI phrases pooled by their
        natural document-volume distribution).

    Returns
    -------
    np.ndarray of shape (n_lenses,) in percentage points.
    """
    pw, valid = _phrase_weights(phrases_df, mixture_weights)
    tech_arr = phrases_df.loc[valid, tech_col].to_numpy()

    ai_mask = tech_arr == "AI"
    non_ai_mask = ~ai_mask

    n_lenses = mixture_weights.shape[1]
    ai_shares = pw[ai_mask].mean(axis=0) if ai_mask.sum() > 0 else np.zeros(n_lenses)

    if baseline == "doc_weighted":
        nonai_shares = (
            pw[non_ai_mask].mean(axis=0)
            if non_ai_mask.sum() > 0
            else np.zeros(n_lenses)
        )
    elif baseline == "tech_weighted":
        non_ai_techs = sorted(set(tech_arr[non_ai_mask].tolist()))
        tech_means = [
            pw[tech_arr == tech].mean(axis=0)
            for tech in non_ai_techs
            if (tech_arr == tech).sum() > 0
        ]
        nonai_shares = (
            np.mean(tech_means, axis=0) if tech_means else np.zeros(n_lenses)
        )
    else:
        raise ValueError(f"Unknown baseline: {baseline!r}")

    return (ai_shares - nonai_shares) * 100.0  # percentage points


# =============================================================================
# Headline evaluation functions ℓ_R1, ℓ_R2, ℓ_R3
# =============================================================================


def ell_R1_cross_cutting_share(
    cluster_entropy: dict[int, float] | dict[str, float],
    threshold: float,
    n_techs: int,
) -> float:
    """Fraction of concern clusters that are cross-cutting at a given threshold.

    Parameters
    ----------
    cluster_entropy:
        Raw Shannon entropy of the technology distribution per cluster.
    threshold:
        Normalised-entropy threshold (0..1) for cross-cutting classification.
    n_techs:
        Number of technologies in the corpus (for normalisation).
    """
    if not cluster_entropy:
        return float("nan")
    max_ent = float(np.log(n_techs)) if n_techs > 1 else 1.0
    cross_cutting = sum(
        1 for _, ent in cluster_entropy.items() if (ent / max_ent) >= threshold
    )
    return cross_cutting / len(cluster_entropy)


def ell_R2_top_ai_pp(
    phrases_df: pd.DataFrame,
    mixture_weights: np.ndarray,
    tech_col: str = "technology_meta",
    baseline: str = "tech_weighted",
) -> float:
    """AI-vs-nonAI pp difference on the lens with the highest AI share.

    Positive values → AI over-indexed on its most salient lens vs the
    chosen non-AI baseline. The "top-AI-salient lens" is picked per
    configuration (its identity may differ across runs), which is the
    multiverse-appropriate framing: the magnitude of the headline
    distinctiveness claim, not a specific lens.
    """
    pw, valid = _phrase_weights(phrases_df, mixture_weights)
    tech_arr = phrases_df.loc[valid, tech_col].to_numpy()
    ai_mask = tech_arr == "AI"
    if ai_mask.sum() == 0:
        return float("nan")

    ai_shares = pw[ai_mask].mean(axis=0)
    top_lens_idx = int(np.argmax(ai_shares))
    pp_diffs = compute_ai_vs_nonai_pp(
        phrases_df, mixture_weights, tech_col=tech_col, baseline=baseline
    )
    return float(pp_diffs[top_lens_idx])


def ell_R3_entropy_stability(
    phrases_df: pd.DataFrame,
    tech_col: str = "technology_meta",
    window_fn: Callable[[int], str] | None = None,
) -> float:
    """Standard deviation of normalised AI concern entropy across time windows.

    Smaller = more "stable spread" interpretation supported.

    If ``window_fn`` is None, imports :func:`pub_dialogue.address.assign_window`.
    """
    if window_fn is None:
        from pub_dialogue.address import assign_window

        window_fn = assign_window

    ai_df = phrases_df[phrases_df[tech_col] == "AI"].copy()
    if ai_df.empty or "year" not in ai_df.columns:
        return float("nan")
    ai_df["time_window"] = ai_df["year"].apply(window_fn)
    ai_df = ai_df.dropna(subset=["time_window"])

    entropies: list[float] = []
    for _, group in ai_df.groupby("time_window"):
        cluster_counts = group["cluster_id"].value_counts()
        if len(cluster_counts) <= 1 or cluster_counts.sum() == 0:
            continue
        probs = (cluster_counts / cluster_counts.sum()).values
        raw_ent = float(scipy_entropy(probs))
        norm_ent = raw_ent / float(np.log(len(cluster_counts)))
        entropies.append(norm_ent)

    if len(entropies) < 2:
        return float("nan")
    return float(np.std(entropies))


# =============================================================================
# Pipeline artifact loader (parameterised by k, prompt)
# =============================================================================


def load_pipeline_artifacts(
    k: int,
    prompt: str,
    output_folder: Path,
    checkpoint_folder: Path,
    load_artifacts_fn: Callable | None = None,
) -> dict[str, Any]:
    """Load the per-(k, prompt) artifact bundle needed to evaluate a configuration.

    For the baseline configuration (k=75, prompt="V0"), this reads the standard
    outputs produced by 01a_clustering.ipynb. For other (k, prompt) pairs it
    raises :class:`NotImplementedError` — plug in the M6b/M6d output paths
    (``cluster_centroids_k{k}.npy``, ``extracted_concerns_prompt{prompt}.csv``,
    etc.) once those are organised on disk.

    Returns
    -------
    Dict with keys:
      - ``concerns_df``
      - ``centroids``
      - ``per_run_mappings``   : list of lens-mapping dicts
      - ``stability_curve``    : pd.DataFrame
      - ``cluster_entropy``    : dict[int, float]
      - ``n_techs``            : int
    """
    if k == 75 and prompt == "V0":
        return _load_baseline_artifacts(
            output_folder, checkpoint_folder, load_artifacts_fn
        )

    raise NotImplementedError(
        f"Expensive dimension (k={k}, prompt={prompt!r}) not yet wired up. "
        "Point this at the M6b/M6d outputs that correspond to this (k, prompt) "
        "and return the same artifact bundle."
    )


def _load_baseline_artifacts(
    output_folder: Path,
    checkpoint_folder: Path,
    load_artifacts_fn: Callable | None,
) -> dict[str, Any]:
    """Baseline artifact bundle at k=75, prompt=V0 (what 01a currently produces)."""
    output_folder = Path(output_folder)
    checkpoint_folder = Path(checkpoint_folder)

    if load_artifacts_fn is None:
        from pub_dialogue.access import load_artifacts as load_artifacts_fn  # type: ignore

    artifacts = load_artifacts_fn(output_folder, checkpoint_folder)

    concerns_df = artifacts["concerns_df"].copy()
    if "technology_meta" not in concerns_df.columns:
        _tech = artifacts["chunks_df"][["chunk_id", "technology_meta"]]
        concerns_df = concerns_df.merge(_tech, on="chunk_id", how="left")

    # Centroids
    centroids_path = checkpoint_folder / "cluster_centroids.npy"
    if "concern_centroids" in artifacts:
        centroids = artifacts["concern_centroids"]
    else:
        centroids = np.load(centroids_path)

    # Per-run lens mappings
    run_files = sorted(output_folder.glob("framing_lens_mappings_run_*.json"))
    per_run_mappings: list[dict] = []
    for p in run_files:
        with open(p) as f:
            per_run_mappings.append(json.load(f))

    # Stability curve
    stability_curve = pd.read_csv(output_folder / "stability_curve_concern.csv")

    # Cluster entropy (raw)
    cluster_entropy_raw = artifacts.get("cluster_entropy", {})
    cluster_entropy = {int(k_): float(v) for k_, v in cluster_entropy_raw.items()}

    n_techs = int(concerns_df["technology_meta"].nunique())

    return {
        "concerns_df": concerns_df,
        "centroids": centroids,
        "per_run_mappings": per_run_mappings,
        "stability_curve": stability_curve,
        "cluster_entropy": cluster_entropy,
        "n_techs": n_techs,
    }


# =============================================================================
# Run one configuration
# =============================================================================


def run_configuration(
    config: MultiverseConfig,
    bundle: dict[str, Any],
    compute_mixture_weights_fn: Callable,
) -> dict[str, Any]:
    """Evaluate one configuration against the three ℓ functions.

    Parameters
    ----------
    config:
        The configuration to evaluate.
    bundle:
        Artifact bundle from :func:`load_pipeline_artifacts` (keyed by
        ``concerns_df``, ``centroids``, ``per_run_mappings``,
        ``stability_curve``, ``cluster_entropy``, ``n_techs``).
    compute_mixture_weights_fn:
        Callable ``(centroids, mapping, sigma2, prior) → (weights, lens_names)``.
        Pass ``AddressStage.compute_mixture_weights``.

    Returns
    -------
    Dict with config fields plus ``sigma2``, ``n_lenses``, ``ell_R1``,
    ``ell_R2``, ``ell_R3``.
    """
    row: dict[str, Any] = config.as_dict()

    # σ² selection
    sigma2_fn = SIGMA2_RULES[config.sigma2_rule]
    sigma2 = sigma2_fn(bundle["stability_curve"])
    row["sigma2"] = sigma2

    # Lens mapping for this draw
    mappings = bundle["per_run_mappings"]
    if not mappings:
        raise RuntimeError("No per-run lens mappings in the artifact bundle.")
    if not (1 <= config.lens_run_idx <= len(mappings)):
        raise ValueError(
            f"lens_run_idx {config.lens_run_idx} out of range 1..{len(mappings)}"
        )
    mapping = mappings[config.lens_run_idx - 1]

    # Mixture weights for this (lens scheme, σ²)
    result = compute_mixture_weights_fn(
        bundle["centroids"], mapping, sigma2, prior="uniform"
    )
    if isinstance(result, tuple):
        mixture_weights, lens_names = result
    else:
        mixture_weights = result
        lens_names = list(mapping.keys())
    row["n_lenses"] = len(lens_names)

    # ℓ_R1 — fraction of cross-cutting clusters at this threshold
    row["ell_R1"] = ell_R1_cross_cutting_share(
        bundle["cluster_entropy"], config.threshold, bundle["n_techs"]
    )

    # ℓ_R2 — AI vs non-AI pp on the top-AI-salient lens
    row["ell_R2"] = ell_R2_top_ai_pp(
        bundle["concerns_df"], mixture_weights, baseline=config.baseline
    )

    # ℓ_R3 — std of normalised entropy across time windows (AI only)
    row["ell_R3"] = ell_R3_entropy_stability(bundle["concerns_df"])

    return row


def run_multiverse(
    configs: list[MultiverseConfig],
    output_folder: Path,
    checkpoint_folder: Path,
    compute_mixture_weights_fn: Callable,
    load_artifacts_fn: Callable | None = None,
    progress: bool = True,
) -> pd.DataFrame:
    """Evaluate every configuration in ``configs`` and return a results frame.

    Bundles are cached per (k, prompt) pair to avoid redundant disk reads.
    """
    if progress:
        try:
            from tqdm.auto import tqdm as _tqdm  # type: ignore
        except ImportError:  # tqdm not installed — fall back to a no-op
            def _tqdm(xs, **_):
                return xs
    else:
        def _tqdm(xs, **_):
            return xs

    bundle_cache: dict[tuple[int, str], dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for cfg in _tqdm(configs, desc="multiverse"):
        key = (cfg.k, cfg.prompt)
        if key not in bundle_cache:
            bundle_cache[key] = load_pipeline_artifacts(
                cfg.k,
                cfg.prompt,
                output_folder,
                checkpoint_folder,
                load_artifacts_fn=load_artifacts_fn,
            )
        row = run_configuration(cfg, bundle_cache[key], compute_mixture_weights_fn)
        rows.append(row)

    return pd.DataFrame(rows)


# =============================================================================
# Variance decomposition
# =============================================================================


def variance_decomposition(
    results_df: pd.DataFrame,
    metric: str,
    dimensions: list[str],
) -> pd.DataFrame:
    """One-way variance share per dimension — first-cut diagnostic.

    For each dimension, computes the between-group sum of squares divided
    by the total sum of squares. **Shares do not sum to 1** in the presence
    of interactions; this is a first-cut diagnostic, not a full ANOVA.
    Use Sobol indices or a full ANOVA for rigorous attribution.
    """
    y = results_df[metric].to_numpy(dtype=float)
    y = y[~np.isnan(y)]
    if y.size == 0:
        return pd.DataFrame({"dimension": dimensions, "variance_share": np.nan})
    grand_mean = float(y.mean())
    total_ss = float(((y - grand_mean) ** 2).sum())
    if total_ss == 0:
        return pd.DataFrame(
            {"dimension": dimensions, "variance_share": [0.0] * len(dimensions)}
        )

    shares = {}
    for dim in dimensions:
        if dim not in results_df.columns:
            shares[dim] = float("nan")
            continue
        between_ss = 0.0
        for _, group in results_df.groupby(dim):
            vals = group[metric].dropna().to_numpy(dtype=float)
            if vals.size == 0:
                continue
            between_ss += vals.size * (float(vals.mean()) - grand_mean) ** 2
        shares[dim] = between_ss / total_ss

    return (
        pd.DataFrame(
            {
                "dimension": dimensions,
                "variance_share": [shares[d] for d in dimensions],
            }
        )
        .sort_values("variance_share", ascending=False)
        .reset_index(drop=True)
    )
