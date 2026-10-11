"""Tests for the multiverse R2 measures (over- and under-indexing)."""

import numpy as np
import pandas as pd
import pytest

from pub_dialogue import multiverse as mv


def _phrases():
    # 3 clusters; cluster i belongs wholly to lens i (identity weights).
    # AI: clusters 0,0,1,1   -> lens shares [0.5, 0.5, 0.0]
    # B : clusters 1,2,2,2   -> [0.0, 0.25, 0.75]
    # C : clusters 0,2,2,2   -> [0.25, 0.0, 0.75]
    rows = [("AI", 0), ("AI", 0), ("AI", 1), ("AI", 1),
            ("B", 1), ("B", 2), ("B", 2), ("B", 2),
            ("C", 0), ("C", 2), ("C", 2), ("C", 2)]
    return pd.DataFrame(rows, columns=["technology_meta", "cluster_id"])


W = np.eye(3)


def test_min_and_max_gaps_tech_weighted():
    # non-AI tech-weighted mean = [0.125, 0.125, 0.75]; AI - nonAI = [+37.5, +37.5, -75] pp
    assert mv.ell_R2_max_pp_gap(_phrases(), W) == pytest.approx(37.5)
    assert mv.ell_R2_min_pp_gap(_phrases(), W) == pytest.approx(-75.0)


def test_min_gap_nan_without_ai():
    df = _phrases()
    df = df[df.technology_meta != "AI"]
    assert np.isnan(mv.ell_R2_min_pp_gap(df, W))


def test_run_configuration_records_lens_names():
    mapping = {"Alpha": {"cluster_ids": [0]}, "Beta": {"cluster_ids": [1]},
               "Gamma": {"cluster_ids": [2]}}
    curve = pd.DataFrame({"sigma2": [0.01, 0.1], "mean_eff_support": [1.0, 1.5],
                          "mean_emd": [0.1, 0.1]})
    bundle = {"per_run_mappings": [mapping], "stability_curve": curve,
              "centroids": np.eye(3), "concerns_df": _phrases()}

    def fake_weights(centroids, mapping, sigma2, prior="uniform"):
        return W, list(mapping.keys())

    cfg = mv.MultiverseConfig(k=75, prompt="V0", lens_run_idx=1,
                              sigma2_rule="constrained", baseline="tech_weighted",
                              threshold=0.5)
    row = mv.run_configuration(cfg, bundle, fake_weights)
    assert row["ell_R2_under"] == pytest.approx(-75.0)
    assert row["R2_under_lens"] == "Gamma"
    assert row["R2_over_lens"] in {"Alpha", "Beta"}
