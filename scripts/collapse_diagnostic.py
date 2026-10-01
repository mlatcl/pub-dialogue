"""
Collapse diagnostic for Bayesian soft-membership lens scheme.

Fits a spherical Gaussian per lens (mean = centroid of its member clusters,
shared variance = sigma^2) and computes per-cluster posteriors over lenses
by Bayes rule.

Reports whether posteriors collapse to near-one-hot (expected in high-dim
with sigma^2 too small) or spread meaningfully.

Run from /workspaces/pub-dialogue:
    python scripts/collapse_diagnostic.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def load_inputs(centroid_path: Path, mapping_path: Path):
    """Load cluster centroids and lens mappings."""
    centroids = np.load(centroid_path)              # (n_clusters, dim)
    with open(mapping_path) as f:
        mappings = json.load(f)
    return centroids, mappings


def compute_posteriors(
    centroids: np.ndarray,
    mappings: dict,
    sigma2: float,
    prior: str = "uniform",
) -> tuple[np.ndarray, list[str]]:
    """Compute P(lens | cluster) for every (cluster, lens).

    Spherical shared-sigma^2 Gaussians, lens means = mean of member cluster
    centroids. Returns a (n_clusters, n_lenses) matrix whose rows sum to 1,
    plus the lens names in matching column order.
    """
    lens_names = list(mappings.keys())
    n_clusters, dim = centroids.shape
    n_lenses = len(lens_names)

    # Compute each lens's mean = mean of its member clusters' centroids
    means = np.zeros((n_lenses, dim))
    counts = np.zeros(n_lenses, dtype=int)
    for i, lens in enumerate(lens_names):
        cids = mappings[lens]["cluster_ids"]
        counts[i] = len(cids)
        if cids:
            means[i] = centroids[cids].mean(axis=0)

    # Log-likelihood under spherical Gaussian:
    #   log p(c|lens) = -||c - mu_lens||^2 / (2 sigma^2) + const
    # The constant is shared across lenses so cancels in normalisation.
    sq_dists = ((centroids[:, None, :] - means[None, :, :]) ** 2).sum(axis=2)
    log_lik = -0.5 * sq_dists / sigma2

    # Prior
    if prior == "uniform":
        log_prior = np.zeros(n_lenses)
    elif prior == "proportional":
        log_prior = np.log(counts / counts.sum())
    else:
        raise ValueError(f"Unknown prior: {prior}")

    log_post = log_lik + log_prior[None, :]
    # Softmax across lenses (per cluster), numerically stable
    log_post -= log_post.max(axis=1, keepdims=True)
    post = np.exp(log_post)
    post /= post.sum(axis=1, keepdims=True)
    return post, lens_names


def summarise(post: np.ndarray, sigma2: float, kind: str) -> dict:
    """Compute collapse diagnostics for one posterior matrix."""
    n_clusters, n_lenses = post.shape

    # Effective support = exp(entropy). 1 = one-hot, n_lenses = uniform.
    with np.errstate(divide="ignore", invalid="ignore"):
        log_p = np.where(post > 0, np.log(post), 0.0)
    entropy = -(post * log_p).sum(axis=1)
    eff_support = np.exp(entropy)

    max_post = post.max(axis=1)

    return {
        "kind": kind,
        "sigma2": sigma2,
        "n_clusters": n_clusters,
        "n_lenses": n_lenses,
        "mean_eff_support": float(eff_support.mean()),
        "median_eff_support": float(np.median(eff_support)),
        "p25_eff_support": float(np.percentile(eff_support, 25)),
        "p75_eff_support": float(np.percentile(eff_support, 75)),
        "mean_max_post": float(max_post.mean()),
        "frac_max_post_above_95": float((max_post > 0.95).mean()),
        "frac_max_post_above_80": float((max_post > 0.80).mean()),
        "frac_max_post_below_50": float((max_post < 0.50).mean()),
    }


def print_summary(rows: list[dict]) -> None:
    """Print the diagnostic table."""
    print()
    print(f"{'kind':<8} {'sigma^2':>10} {'n_lenses':>9} "
          f"{'mean_eff':>9} {'median_eff':>11} {'IQR_eff':>13} "
          f"{'mean_max_p':>11} {'>.95':>7} {'>.80':>7} {'<.50':>7}")
    print("-" * 110)
    for r in rows:
        iqr = f"[{r['p25_eff_support']:.2f}, {r['p75_eff_support']:.2f}]"
        print(f"{r['kind']:<8} {r['sigma2']:>10.4g} {r['n_lenses']:>9d} "
              f"{r['mean_eff_support']:>9.3f} {r['median_eff_support']:>11.3f} "
              f"{iqr:>13} {r['mean_max_post']:>11.3f} "
              f"{r['frac_max_post_above_95']:>7.2f} "
              f"{r['frac_max_post_above_80']:>7.2f} "
              f"{r['frac_max_post_below_50']:>7.2f}")


def main() -> None:
    outputs = Path("outputs")
    checkpoints = Path("checkpoints")

    sides = [
        ("concern", checkpoints / "cluster_centroids.npy",
         outputs / "framing_lens_mappings.json"),
        ("benefit", checkpoints / "cluster_centroids_benefit.npy",
         outputs / "benefit_framing_lens_mappings.json"),
    ]

    # A sweep of sigma^2 values across many orders of magnitude.
    # Expected narrative:
    #   - very small sigma^2 → full collapse (eff support ≈ 1, max_p ≈ 1)
    #   - very large sigma^2 → full uniform (eff support ≈ n_lenses, max_p ≈ 1/n_lenses)
    #   - somewhere in between there's a transition region
    sigma2_grid = [1e-4, 1e-3, 1e-2, 1e-1, 1e+0, 1e+1, 1e+2]

    rows = []
    for kind, cpath, mpath in sides:
        if not cpath.exists():
            print(f"[WARN] missing {cpath} — skipping {kind}")
            continue
        if not mpath.exists():
            print(f"[WARN] missing {mpath} — skipping {kind}")
            continue
        centroids, mappings = load_inputs(cpath, mpath)
        print(f"\n[{kind}] centroids: {centroids.shape}, lenses: {len(mappings)}")
        for sigma2 in sigma2_grid:
            post, _ = compute_posteriors(centroids, mappings, sigma2)
            rows.append(summarise(post, sigma2, kind))

    print_summary(rows)
    print()
    print("Reading the table:")
    print("  mean_eff   = mean exp(entropy) across 75 clusters.")
    print("                1.0 = one-hot (collapsed); n_lenses = uniform.")
    print("  mean_max_p = mean of per-cluster max posterior.")
    print("  >.95       = fraction of clusters whose top lens exceeds 95% posterior.")
    print("  <.50       = fraction of clusters whose top lens is below 50% (soft).")


if __name__ == "__main__":
    main()
