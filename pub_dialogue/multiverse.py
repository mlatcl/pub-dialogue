"""Multiverse analysis for the public dialogue paper.

Produces the Cartesian product of defensible analytical choices and
evaluates each configuration against the three headline findings
(R1 shared structure; R2 AI distinctiveness; R3 temporal stability).

Dimensions (cheap — no additional LLM calls, reuse existing artifacts):
  - lens_run_idx : 1..N (reuses ``outputs/framing_lens_mappings_run_*.json``)
    - sigma2_rule  : softness band used to pick σ² on the stability curve
                   (constrained = the canonical 01a rule; one grid step
                   harder / softer; hard = no smoothing)
  - baseline     : tech-weighted vs doc-weighted non-AI baseline (R2 only)
  - threshold    : share of technologies a cluster must reach to count as
                   cross-cutting under the coverage measure (R1 only)

Dimensions (modest extra cost — one-time setup via ``prepare_k_variant``):
  - k : 60, 75, 90 (reclusters existing embeddings at new k, regenerates
                    lens mappings and σ² sweep; prompt stays V0)

Dimensions (expensive — require full re-extraction, stubbed):
  - prompt : V0, V1, V3 (would need the whole corpus re-extracted under
                         each prompt variant; currently only V0 is supported)

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
from pub_dialogue.address import CONCERN_PROMPT_VARIANTS

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
    sigma2_rule: str = "constrained"
    baseline: str = "tech_weighted"
    threshold: float = 0.5

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# =============================================================================
# Enumeration
# =============================================================================


def enumerate_configurations(dimensions: dict[str, list]) -> list[MultiverseConfig]:
    """Build the full Cartesian product of a dimensions dict."""
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


# The canonical rule (used for every headline result, via
# ``AddressStage.sigma2_sweep_select`` in 01a) picks the σ² with the lowest
# mean EMD between lens runs, among σ² values whose mean effective support
# (the effective number of lenses each cluster spreads over) lies strictly
# inside (0.2, 0.6) × the mean number of lenses.  Without that band the
# minimum-EMD σ² is the degenerate near-uniform solution, where every cluster
# belongs almost equally to every lens and AI-vs-non-AI differences vanish.
CANONICAL_SUPPORT_BAND: tuple[float, float] = (0.2, 0.6)


def select_sigma2_in_band(
    stability_curve: pd.DataFrame,
    n_lenses: float,
    band: tuple[float, float] = CANONICAL_SUPPORT_BAND,
) -> float:
    """Min-EMD σ² among rows with ``band[0]·n < eff_support < band[1]·n``.

    Falls back to the unconstrained minimum-EMD row if no σ² lies in the
    band — exactly as ``AddressStage.sigma2_sweep_select`` does.
    """
    low, high = band[0] * n_lenses, band[1] * n_lenses
    inside = stability_curve[
        (stability_curve["mean_eff_support"] > low)
        & (stability_curve["mean_eff_support"] < high)
    ]
    pool = inside if not inside.empty else stability_curve
    return float(pool.loc[pool["mean_emd"].idxmin(), "sigma2"])


def select_sigma2_constrained(stability_curve: pd.DataFrame, n_lenses: float) -> float:
    """The canonical rule: band (0.2, 0.6) × n_lenses.  Reproduces 01a's σ²*."""
    return select_sigma2_in_band(stability_curve, n_lenses, CANONICAL_SUPPORT_BAND)


def _neighbour_on_grid(stability_curve: pd.DataFrame, n_lenses: float, step: int) -> float:
    """σ² *step* grid points away from the canonical choice (clipped to the grid)."""
    grid = np.sort(stability_curve["sigma2"].to_numpy(dtype=float))
    canonical = select_sigma2_constrained(stability_curve, n_lenses)
    i = int(np.argmin(np.abs(grid - canonical)))
    return float(grid[min(max(i + step, 0), len(grid) - 1)])


def select_sigma2_one_step_harder(stability_curve: pd.DataFrame, n_lenses: float) -> float:
    """Grid point just below the canonical σ² — each cluster spreads over
    fewer lenses (sharper memberships)."""
    return _neighbour_on_grid(stability_curve, n_lenses, -1)


def select_sigma2_one_step_softer(stability_curve: pd.DataFrame, n_lenses: float) -> float:
    """Grid point just above the canonical σ² — each cluster spreads over
    more lenses (softer memberships)."""
    return _neighbour_on_grid(stability_curve, n_lenses, +1)


def select_sigma2_hard(stability_curve: pd.DataFrame, n_lenses: float) -> float:
    """Smallest σ² swept — effectively hard assignment of each cluster to
    its best-fitting lens.  A no-smoothing reference point."""
    return float(stability_curve["sigma2"].min())


SIGMA2_RULES: dict[str, Callable[[pd.DataFrame, float], float]] = {
    "constrained": select_sigma2_constrained,
    "one_step_harder": select_sigma2_one_step_harder,
    "one_step_softer": select_sigma2_one_step_softer,
    "hard": select_sigma2_hard,
}


# --- Legacy rules (pre-October 2026). Kept so old results can be reproduced;
# --- not used by default.  Both select σ² values unrelated to the headline:
# --- "min_emd" lands on the degenerate near-uniform solution, and "median"
# --- is the middle of the σ² grid regardless of the data.
def select_sigma2_min_emd(stability_curve: pd.DataFrame, n_lenses: float = 0.0) -> float:
    """LEGACY: unconstrained minimum-EMD row (degenerate near-uniform σ²)."""
    idx = stability_curve["mean_emd"].idxmin()
    return float(stability_curve.loc[idx, "sigma2"])


def select_sigma2_median(stability_curve: pd.DataFrame, n_lenses: float = 0.0) -> float:
    """LEGACY: median of the σ² grid (not data-driven)."""
    return float(stability_curve["sigma2"].median())


LEGACY_SIGMA2_RULES: dict[str, Callable[[pd.DataFrame, float], float]] = {
    "min_emd": select_sigma2_min_emd,
    "median": select_sigma2_median,
}


def mean_n_lenses(per_run_mappings: list[dict]) -> float:
    """Mean number of lenses across lens runs — the n in the support band."""
    return float(np.mean([len(m) for m in per_run_mappings]))


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
    """Return per-lens AI vs non-AI pp difference under the chosen baseline."""
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
    phrases_df: pd.DataFrame,
    threshold: float,
    n_clusters: int,
    tech_col: str = "technology_meta",
) -> float:
    """Fraction of concern clusters that are cross-cutting under the coverage
    measure (see pub_dialogue.crosscut).  ``threshold`` is the share of
    technologies a cluster must reach (min_fraction), e.g. 0.5 = 6 of 12."""
    from pub_dialogue.crosscut import classify_crosscutting

    if phrases_df is None or phrases_df.empty:
        return float("nan")
    clusters, _ = classify_crosscutting(
        phrases_df, n_clusters, tech_col=tech_col, min_fraction=threshold, n_perm=0
    )
    return float(clusters["cross_cutting"].mean())


def ell_R2_max_pp_gap(
    phrases_df: pd.DataFrame,
    mixture_weights: np.ndarray,
    tech_col: str = "technology_meta",
    baseline: str = "tech_weighted",
) -> float:
    """Largest AI-vs-nonAI pp difference across any lens.

    Positive values → AI is over-indexed on some lens by this many
    percentage points, vs the chosen non-AI baseline. The identity of
    the most distinctive lens may differ across configurations — this
    is the multiverse-appropriate framing: the magnitude of the
    distinctiveness claim, not a specific lens.
    """
    _pw, valid = _phrase_weights(phrases_df, mixture_weights)
    tech_arr = phrases_df.loc[valid, tech_col].to_numpy()
    if (tech_arr == "AI").sum() == 0:
        return float("nan")

    pp_diffs = compute_ai_vs_nonai_pp(
        phrases_df, mixture_weights, tech_col=tech_col, baseline=baseline
    )
    return float(pp_diffs.max())


def ell_R3_entropy_stability(
    phrases_df: pd.DataFrame,
    tech_col: str = "technology_meta",
    window_fn: Callable[[int], str] | None = None,
) -> float:
    """Standard deviation of normalised AI concern entropy across time windows."""
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
# One-time setup: prepare k-variant artifacts (k != 75, prompt == V0)
# =============================================================================


def prepare_k_variant(
    k: int,
    output_folder: Path,
    checkpoint_folder: Path,
    address_stage: Any,
    access_stage: Any,
    client: Any,
    n_lens_runs: int = 5,
    source_prompt: str = "V0",
    overwrite: bool = False,
) -> Path:
    """One-time setup: run the clustering + lens pipeline at a non-canonical k.

    Reuses the canonical concern-phrase extraction (prompt='V0') but re-clusters
    the existing embeddings at the specified k and regenerates all downstream
    artifacts (cluster labels, exemplars, cluster entropy, N lens mappings,
    σ² sweep). Writes everything to:

        ``{output_folder}/multiverse_sources/k{k}_{source_prompt}/``
        ``{checkpoint_folder}/multiverse_sources/k{k}_{source_prompt}/``

    Only ``source_prompt='V0'`` is supported — other prompt variants would
    require full corpus re-extraction, which is out of scope for this helper.

    Parameters
    ----------
    k:
        New number of concern clusters.
    output_folder, checkpoint_folder:
        The canonical top-level folders; subfolders are created under each.
    address_stage:
        An ``AddressStage`` instance; its ``n_concern_clusters`` attribute is
        temporarily patched to ``k`` for the duration of this call.
    access_stage:
        An ``AccessStage`` instance (used to load canonical artifacts).
    client:
        LLMClient — needed for cluster labelling and lens generation.
    n_lens_runs:
        Number of independent LLM lens-grouping runs to feed the σ² sweep.
    source_prompt:
        Which prompt variant's phrase extraction to reuse (currently only "V0").
    overwrite:
        If False (default) and the per-k subfolder already contains the key
        artifacts, skip the setup. If True, re-run.

    Returns
    -------
    The ``Path`` of the per-k output subfolder.
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import normalize
    from scipy.stats import entropy as _entropy

    if source_prompt != "V0":
        raise NotImplementedError(
            "prepare_k_variant currently only supports source_prompt='V0'. "
            "Other prompt variants would require full corpus re-extraction."
        )

    output_folder = Path(output_folder)
    checkpoint_folder = Path(checkpoint_folder)
    out_sub = output_folder / "multiverse_sources" / f"k{k}_{source_prompt}"
    ckpt_sub = checkpoint_folder / "multiverse_sources" / f"k{k}_{source_prompt}"
    out_sub.mkdir(parents=True, exist_ok=True)
    ckpt_sub.mkdir(parents=True, exist_ok=True)

    # Short-circuit if already prepared
    key_files = [
        ckpt_sub / "cluster_centroids.npy",
        out_sub / "stability_curve_concern.csv",
        out_sub / "framing_lens_mappings_run_1.json",
    ]
    if not overwrite and all(f.exists() for f in key_files):
        print(f"[k={k}] already prepared at {out_sub} — skipping (set overwrite=True to force)")
        return out_sub

    print(f"[k={k}] preparing variant at {out_sub}")

    # --- 1. Load canonical artifacts (concern phrases + embeddings) ---
    artifacts = access_stage.load_artifacts()
    concerns_df = artifacts["concerns_df"].copy()
    if "technology_meta" not in concerns_df.columns:
        _tech = artifacts["chunks_df"][["chunk_id", "technology_meta"]]
        concerns_df = concerns_df.merge(_tech, on="chunk_id", how="left")
    concern_embeddings = artifacts["concern_embeddings"]

    # --- 2. KMeans at k ---
    print(f"[k={k}] clustering embeddings...")
    embeddings_normalized = normalize(concern_embeddings)
    km = KMeans(
        n_clusters=k,
        random_state=getattr(address_stage, "random_seed", 42),
        n_init="auto",
    )
    cluster_assignments = km.fit_predict(embeddings_normalized)
    centroids_normalized = normalize(km.cluster_centers_)
    concerns_df["cluster_id"] = cluster_assignments

    np.save(ckpt_sub / "cluster_centroids.npy", centroids_normalized)
    concerns_df.to_csv(out_sub / "extracted_concerns.csv", index=False)

    # --- 3. Cluster entropy by technology ---
    cluster_entropy: dict[int, float] = {}
    for cid in range(k):
        mask = concerns_df["cluster_id"] == cid
        if mask.sum() == 0:
            cluster_entropy[cid] = 0.0
            continue
        probs = concerns_df.loc[mask, "technology_meta"].value_counts(normalize=True)
        cluster_entropy[cid] = float(_entropy(probs.values))

   with open(out_sub / "cluster_entropy.json", "w") as f:
        json.dump(
            {"raw": {str(k_): v for k_, v in cluster_entropy.items()}},
            f,
            indent=2,
        )

    # Cross-cutting flags for cluster labelling: coverage measure (crosscut.py)
    from pub_dialogue.crosscut import classify_crosscutting
    _xc, _ = classify_crosscutting(concerns_df, k, n_perm=0)
    _xc_flags = dict(zip(_xc["cluster_id"].astype(int), _xc["cross_cutting"].astype(bool)))

    # --- 4. Extract per-cluster exemplars (for cluster labelling) ---
    print(f"[k={k}] extracting exemplars...")
    N_EXEMPLARS = 8
    cluster_exemplars: dict[int, dict[str, Any]] = {}
    for cid in range(k):
        mask = concerns_df["cluster_id"] == cid
        if mask.sum() == 0:
            continue
        cluster_concerns = concerns_df[mask]
        cluster_embs = embeddings_normalized[mask.to_numpy()]
        centroid = centroids_normalized[cid]
        sims = cosine_similarity(cluster_embs, centroid.reshape(1, -1)).flatten()
        top = np.argsort(sims)[-N_EXEMPLARS:][::-1]
        exemplars = []
        for idx in top:
            row = cluster_concerns.iloc[idx]
            exemplars.append(
                {
                    "concern": row["concern"],
                    "technology": row.get("technology", row.get("technology_meta", "")),
                    "year": int(row["year"]) if pd.notna(row.get("year")) else None,
                    "similarity": float(sims[idx]),
                }
            )
        tech_dist = (
            cluster_concerns.get("technology", cluster_concerns["technology_meta"])
            .value_counts()
            .head(3)
            .to_dict()
        )
        max_ent_norm = float(np.log(concerns_df["technology_meta"].nunique()))
        cluster_exemplars[cid] = {
            "size": int(mask.sum()),
            "entropy": cluster_entropy[cid] / max_ent_norm if max_ent_norm > 0 else 0.0,
            "is_cross_cutting": bool(_xc_flags.get(cid, False)),
            "top_technologies": tech_dist,
            "exemplars": exemplars,
        }

    with open(out_sub / "cluster_exemplars.json", "w") as f:
        json.dump(cluster_exemplars, f, indent=2, default=str)

    # --- 5. Patch address_stage to use the new k, then label and lens-gen ---
    original_k = getattr(address_stage, "n_concern_clusters", None)
    try:
        address_stage.n_concern_clusters = k

        print(f"[k={k}] labelling clusters (LLM)...")
        cluster_labels_dict = address_stage.label_clusters(
            cluster_exemplars,
            kind="concern",
            output_folder=out_sub,
            client=client,
        )

        print(f"[k={k}] generating {n_lens_runs} lens mappings (LLM)...")
        _, _stability = address_stage.generate_lens_grouping_multi(
            cluster_exemplars,
            cluster_labels_dict,
            k,
            "concern",
            client,
            centroids_normalized=centroids_normalized,
            n_runs=n_lens_runs,
            output_folder=out_sub,
        )
      
        print(f"[k={k}] loading per-run mappings and running σ² sweep...")
        # Glob for the mappings that actually got saved — some runs may have
        # failed (e.g. LLM-returned JSON with C-style comments that Python
        # can't parse). generate_lens_grouping_multi catches those as warnings
        # but can leave gaps in the numbered sequence, which would make the
        # strict load_per_run_mappings error out.
        run_files = sorted(
            out_sub.glob("framing_lens_mappings_run_*.json"),
            key=lambda p: int(p.stem.rsplit("_", 1)[-1]),
        )
        if not run_files:
            raise RuntimeError(
                f"[k={k}] no lens-grouping runs succeeded — cannot proceed"
            )
        if len(run_files) < n_lens_runs:
            print(
                f"[k={k}] WARNING: only {len(run_files)}/{n_lens_runs} "
                f"lens-grouping runs succeeded; proceeding with those."
            )
        per_run_mappings = [json.loads(p.read_text()) for p in run_files]

        address_stage.sigma2_sweep_select(
            centroids=centroids_normalized,
            mappings_list=per_run_mappings,
            kind="concern",
            output_folder=out_sub,
        )
    finally:
        if original_k is not None:
            address_stage.n_concern_clusters = original_k

    print(f"[k={k}] done. Artifacts at {out_sub}")
    return out_sub

def prepare_prompt_variant(
    prompt: str,
    k: int,
    output_folder: Path,
    checkpoint_folder: Path,
    address_stage: Any,
    access_stage: Any,
    client: Any,
    n_lens_runs: int = 5,
    overwrite: bool = False,
    extract_phrases_fn: Callable | None = None,
    get_embeddings_batch_fn: Callable | None = None,
) -> Path:
    """One-time setup: run the full extraction + clustering + lens pipeline
    at a non-canonical (prompt, k) point.

    Re-extracts concern phrases from all chunks under the specified prompt
    variant, re-embeds, re-clusters at k, labels, generates N lens groupings,
    and runs σ² sweep. Writes to
    ``{output_folder}/multiverse_sources/k{k}_{prompt}/``.

    For (prompt='V0'), delegates to :func:`prepare_k_variant` (no extraction
    needed; reuses the canonical corpus).

    Parameters
    ----------
    prompt:
        Prompt variant name (``"V0"``, ``"V1"``, or ``"V3"`` — must match the
        variants defined in your extraction code).
    k:
        Number of concern clusters.
    extract_phrases_fn:
        Optional override for the phrase-extraction function. Defaults to
        ``pub_dialogue.utils.extract_phrases``. Must accept
        ``(row, kind, client, prompt_variant=...)`` and return an object with
        ``.chunk_id`` and ``.retained_phrases`` attributes.
    get_embeddings_batch_fn:
        Optional override for the embedding batcher. Defaults to
        ``pub_dialogue.utils.get_embeddings_batch``.
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import normalize
    from scipy.stats import entropy as _entropy

    # V0 delegates to the k-only variant (no re-extraction)
    if prompt == "V0":
        return prepare_k_variant(
            k=k,
            output_folder=output_folder,
            checkpoint_folder=checkpoint_folder,
            address_stage=address_stage,
            access_stage=access_stage,
            client=client,
            n_lens_runs=n_lens_runs,
            source_prompt="V0",
            overwrite=overwrite,
        )

    if extract_phrases_fn is None:
        from pub_dialogue.utils import extract_phrases as extract_phrases_fn  # type: ignore
    if get_embeddings_batch_fn is None:
        from pub_dialogue.utils import get_embeddings_batch as get_embeddings_batch_fn  # type: ignore

    output_folder = Path(output_folder)
    checkpoint_folder = Path(checkpoint_folder)
    out_sub = output_folder / "multiverse_sources" / f"k{k}_{prompt}"
    ckpt_sub = checkpoint_folder / "multiverse_sources" / f"k{k}_{prompt}"
    out_sub.mkdir(parents=True, exist_ok=True)
    ckpt_sub.mkdir(parents=True, exist_ok=True)

    # Short-circuit if already prepared
    key_files = [
        ckpt_sub / "cluster_centroids.npy",
        out_sub / "stability_curve_concern.csv",
        out_sub / "framing_lens_mappings_run_1.json",
    ]
    if not overwrite and all(f.exists() for f in key_files):
        print(f"[prompt={prompt}, k={k}] already prepared at {out_sub} — skipping")
        return out_sub

    print(f"[prompt={prompt}, k={k}] preparing variant at {out_sub}")

    # --- 1. Load chunks ---
    artifacts = access_stage.load_artifacts()
    chunks_df = artifacts["chunks_df"].copy()

    # --- 2. Re-extract concern phrases under the new prompt ---
    extracted_path = out_sub / "extracted_concerns.csv"
    if extracted_path.exists() and not overwrite:
        print(f"[prompt={prompt}] loading cached extractions from {extracted_path}")
        concerns_df = pd.read_csv(extracted_path)
    else:
        print(f"[prompt={prompt}] extracting from {len(chunks_df)} chunks (LLM)...")
        from concurrent.futures import ThreadPoolExecutor, as_completed
        try:
            from tqdm.auto import tqdm as _tqdm  # type: ignore
        except ImportError:
            def _tqdm(x, **_):
                return x

        all_concerns: dict[str, list] = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(
                    extract_phrases_fn, row, "concern", client,
                    prompt_template=CONCERN_PROMPT_VARIANTS[prompt],
                ): row[1]["chunk_id"]
                for row in chunks_df.iterrows()
            }
            for fut in _tqdm(as_completed(futures), total=len(futures), desc=f"Extracting ({prompt})"):
                res = fut.result()
                all_concerns[res.chunk_id] = res.retained_phrases

        concern_rows = []
        for chunk_id, phrases in all_concerns.items():
            meta_row = chunks_df[chunks_df["chunk_id"] == chunk_id].iloc[0]
            for concern in phrases:
                concern_rows.append({
                    "chunk_id": chunk_id,
                    "concern": concern,
                    "technology_meta": meta_row.get("technology_meta", ""),
                    "year": int(meta_row["year"]) if pd.notna(meta_row.get("year")) else None,
                    "source_file": meta_row.get("source_file", ""),
                })
        concerns_df = pd.DataFrame(concern_rows)
        concerns_df["concern_id"] = [f"concern_{i}" for i in range(len(concerns_df))]
        concerns_df.to_csv(extracted_path, index=False)

    # --- 3. Embed ---
    embeddings_path = ckpt_sub / "concern_embeddings.npy"
    if embeddings_path.exists() and not overwrite:
        print(f"[prompt={prompt}] loading cached embeddings from {embeddings_path}")
        concern_embeddings = np.load(embeddings_path)
    else:
        print(f"[prompt={prompt}] embedding {len(concerns_df)} phrases...")
        texts = concerns_df["concern"].tolist()
        all_emb = []
        BATCH = 100
        for i in range(0, len(texts), BATCH):
            all_emb.append(get_embeddings_batch_fn(texts[i : i + BATCH], client))
        concern_embeddings = np.vstack(all_emb)
        np.save(embeddings_path, concern_embeddings)

    # --- 4. KMeans + 5-7: entropy, exemplars, label, lens-gen, σ² sweep ---
    # (Everything below mirrors prepare_k_variant — same structure)
    print(f"[prompt={prompt}, k={k}] clustering...")
    embeddings_normalized = normalize(concern_embeddings)
    km = KMeans(
        n_clusters=k,
        random_state=getattr(address_stage, "random_seed", 42),
        n_init="auto",
    )
    cluster_assignments = km.fit_predict(embeddings_normalized)
    centroids_normalized = normalize(km.cluster_centers_)
    concerns_df["cluster_id"] = cluster_assignments

    np.save(ckpt_sub / "cluster_centroids.npy", centroids_normalized)
    concerns_df.to_csv(extracted_path, index=False)

    cluster_entropy = {}
    for cid in range(k):
        mask = concerns_df["cluster_id"] == cid
        if mask.sum() == 0:
            cluster_entropy[cid] = 0.0
            continue
        probs = concerns_df.loc[mask, "technology_meta"].value_counts(normalize=True)
        cluster_entropy[cid] = float(_entropy(probs.values))
    with open(out_sub / "cluster_entropy.json", "w") as f:
        json.dump({"raw": {str(cid): v for cid, v in cluster_entropy.items()}}, f, indent=2)

    # Cross-cutting flags for cluster labelling: coverage measure (crosscut.py)
    from pub_dialogue.crosscut import classify_crosscutting
    _xc, _ = classify_crosscutting(concerns_df, k, n_perm=0)
    _xc_flags = dict(zip(_xc["cluster_id"].astype(int), _xc["cross_cutting"].astype(bool)))

    print(f"[prompt={prompt}, k={k}] extracting exemplars...")
    N_EXEMPLARS = 8
    cluster_exemplars = {}
    for cid in range(k):
        mask = concerns_df["cluster_id"] == cid
        if mask.sum() == 0:
            continue
        cluster_concerns = concerns_df[mask]
        cluster_embs = embeddings_normalized[mask.to_numpy()]
        centroid = centroids_normalized[cid]
        sims = cosine_similarity(cluster_embs, centroid.reshape(1, -1)).flatten()
        top = np.argsort(sims)[-N_EXEMPLARS:][::-1]
        exemplars = []
        for idx in top:
            row = cluster_concerns.iloc[idx]
            exemplars.append({
                "concern": row["concern"],
                "technology": row.get("technology", row.get("technology_meta", "")),
                "year": int(row["year"]) if pd.notna(row.get("year")) else None,
                "similarity": float(sims[idx]),
            })
        tech_dist = (
            cluster_concerns.get("technology", cluster_concerns["technology_meta"])
            .value_counts().head(3).to_dict()
        )
        max_ent_norm = float(np.log(concerns_df["technology_meta"].nunique()))
        cluster_exemplars[cid] = {
            "size": int(mask.sum()),
            "entropy": cluster_entropy[cid] / max_ent_norm if max_ent_norm > 0 else 0.0,
            "is_cross_cutting": bool(_xc_flags.get(cid, False)),
            "top_technologies": tech_dist,
            "exemplars": exemplars,
        }
    with open(out_sub / "cluster_exemplars.json", "w") as f:
        json.dump(cluster_exemplars, f, indent=2, default=str)

    original_k = getattr(address_stage, "n_concern_clusters", None)
    try:
        address_stage.n_concern_clusters = k

        print(f"[prompt={prompt}, k={k}] labelling clusters (LLM)...")
        cluster_labels_dict = address_stage.label_clusters(
            cluster_exemplars, kind="concern", output_folder=out_sub, client=client,
        )
        print(f"[prompt={prompt}, k={k}] generating {n_lens_runs} lens mappings (LLM)...")
        address_stage.generate_lens_grouping_multi(
            cluster_exemplars, cluster_labels_dict, k, "concern", client,
            centroids_normalized=centroids_normalized,
            n_runs=n_lens_runs, output_folder=out_sub,
        )
        print(f"[prompt={prompt}, k={k}] σ² sweep...")
        run_files = sorted(
            out_sub.glob("framing_lens_mappings_run_*.json"),
            key=lambda p: int(p.stem.rsplit("_", 1)[-1]),
        )
        if not run_files:
            raise RuntimeError(f"[prompt={prompt}, k={k}] no lens-grouping runs succeeded")
        per_run_mappings = [json.loads(p.read_text()) for p in run_files]
        address_stage.sigma2_sweep_select(
            centroids=centroids_normalized,
            mappings_list=per_run_mappings,
            kind="concern",
            output_folder=out_sub,
        )
    finally:
        if original_k is not None:
            address_stage.n_concern_clusters = original_k

    print(f"[prompt={prompt}, k={k}] done. Artifacts at {out_sub}")
    return out_sub

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
    """Load the per-(k, prompt) artifact bundle for one configuration.

    - (k=75, V0): reads canonical artifacts via ``load_artifacts_fn``.
    - (k∈{60, 90}, V0): reads from ``outputs/multiverse_sources/k{k}_V0/``
      (populated via :func:`prepare_k_variant`).
    - Other (k, prompt) pairs: raises :class:`NotImplementedError`.

    Returns
    -------
    Dict with keys ``concerns_df``, ``centroids``, ``per_run_mappings``,
    ``stability_curve``, ``cluster_entropy``, ``n_techs``.
    """
    output_folder = Path(output_folder)
    checkpoint_folder = Path(checkpoint_folder)

    if k == 75 and prompt == "V0":
        return _load_baseline_artifacts(
            output_folder, checkpoint_folder, load_artifacts_fn
        )

    if (prompt == "V0" and k in (60, 90)) or (k == 75 and prompt in ("C_no_decon", "B_broader")):
        subdir_out = output_folder / "multiverse_sources" / f"k{k}_{prompt}"
        subdir_ckpt = checkpoint_folder / "multiverse_sources" / f"k{k}_{prompt}"
        if not subdir_out.exists() or not (subdir_ckpt / "cluster_centroids.npy").exists():
            raise FileNotFoundError(
                f"No prepared artifacts for k={k}, prompt='{prompt}' at "
                f"{subdir_out}. Run multiverse.prepare_k_variant(k={k}, ...) "
                "first to generate them."
            )
        return _load_variant_artifacts(subdir_out, subdir_ckpt, output_folder)

    raise NotImplementedError(
        f"Expensive dimension (k={k}, prompt={prompt!r}) not yet wired up. "
        "Prompt variants other than 'V0' would require full re-extraction "
        "of the corpus."
    )


def _load_baseline_artifacts(
    output_folder: Path,
    checkpoint_folder: Path,
    load_artifacts_fn: Callable | None,
) -> dict[str, Any]:
    """Baseline artifact bundle at k=75, prompt=V0 (what 01a currently produces)."""
    if load_artifacts_fn is None:
        from pub_dialogue.access import load_artifacts as load_artifacts_fn  # type: ignore

    artifacts = load_artifacts_fn(output_folder, checkpoint_folder)

    concerns_df = artifacts["concerns_df"].copy()
    if "technology_meta" not in concerns_df.columns:
        _tech = artifacts["chunks_df"][["chunk_id", "technology_meta"]]
        concerns_df = concerns_df.merge(_tech, on="chunk_id", how="left")

    centroids_path = checkpoint_folder / "cluster_centroids.npy"
    if "concern_centroids" in artifacts:
        centroids = artifacts["concern_centroids"]
    else:
        centroids = np.load(centroids_path)

    run_files = sorted(output_folder.glob("framing_lens_mappings_run_*.json"))
    per_run_mappings: list[dict] = []
    for p in run_files:
        with open(p) as f:
            per_run_mappings.append(json.load(f))

    stability_curve = pd.read_csv(output_folder / "stability_curve_concern.csv")

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


def _load_variant_artifacts(
    subdir_out: Path,
    subdir_ckpt: Path,
    canonical_output_folder: Path,
) -> dict[str, Any]:
    """Per-k artifact bundle (populated by :func:`prepare_k_variant`)."""
    # Concerns re-saved with new cluster_id by prepare_k_variant
    concerns_df = pd.read_csv(subdir_out / "extracted_concerns.csv")

    centroids = np.load(subdir_ckpt / "cluster_centroids.npy")

    run_files = sorted(subdir_out.glob("framing_lens_mappings_run_*.json"))
    per_run_mappings: list[dict] = []
    for p in run_files:
        with open(p) as f:
            per_run_mappings.append(json.load(f))

    stability_curve = pd.read_csv(subdir_out / "stability_curve_concern.csv")

    with open(subdir_out / "cluster_entropy.json") as f:
        entropy_dict = json.load(f)
    raw = entropy_dict.get("raw", entropy_dict)
    cluster_entropy = {int(k_): float(v) for k_, v in raw.items()}

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
    """Evaluate one configuration against the three ℓ functions."""
    row: dict[str, Any] = config.as_dict()

    mappings = bundle["per_run_mappings"]
    if not mappings:
        raise RuntimeError("No per-run lens mappings in the artifact bundle.")

    rules = {**SIGMA2_RULES, **LEGACY_SIGMA2_RULES}
    if config.sigma2_rule not in rules:
        raise ValueError(f"Unknown sigma2_rule {config.sigma2_rule!r}; "
                         f"choose from {list(SIGMA2_RULES)}")
    sigma2 = rules[config.sigma2_rule](bundle["stability_curve"],
                                       mean_n_lenses(mappings))
    row["sigma2"] = sigma2
    if not (1 <= config.lens_run_idx <= len(mappings)):
        raise ValueError(
            f"lens_run_idx {config.lens_run_idx} out of range 1..{len(mappings)}"
        )
    mapping = mappings[config.lens_run_idx - 1]

    result = compute_mixture_weights_fn(
        bundle["centroids"], mapping, sigma2, prior="uniform"
    )
    if isinstance(result, tuple):
        mixture_weights, lens_names = result
    else:
        mixture_weights = result
        lens_names = list(mapping.keys())
    row["n_lenses"] = len(lens_names)

    row["ell_R1"] = ell_R1_cross_cutting_share(
        bundle["concerns_df"], config.threshold, bundle["centroids"].shape[0]
    )
    row["ell_R2"] = ell_R2_max_pp_gap(
        bundle["concerns_df"], mixture_weights, baseline=config.baseline
    )
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
    """Evaluate every configuration in ``configs`` and return a results frame."""
    if progress:
        try:
            from tqdm.auto import tqdm as _tqdm  # type: ignore
        except ImportError:
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

    Shares do not sum to 1 in the presence of interactions. Use Sobol
    indices or a full ANOVA for rigorous attribution.
    """
    y = results_df[metric].to_numpy(dtype=float)
    y = y[~np.isnan(y)]
    if y.size == 0:
        return pd.DataFrame({"dimension": dimensions, "variance_share": np.nan})
    grand_mean = float(y.mean())
    total_ss = float(((y - grand_mean) ** 2).sum())

    # Protect against floating-point noise: if the metric is effectively
    # constant across the multiverse, treat total variance as zero rather
    # than dividing by near-zero and getting spurious variance shares.
    noise_floor = 1e-10 * (abs(grand_mean) + 1e-12)
    if total_ss <= noise_floor:
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
