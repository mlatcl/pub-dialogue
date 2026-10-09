"""Tests for pub_dialogue.crosscut (coverage-based cross-cutting measure)."""

import json

import numpy as np
import pandas as pd
import pytest

from pub_dialogue import crosscut as cc


def _corpus(spec, seed=0):
    """spec: {technology: [(doc, profile, n_phrases), ...]} -> phrase table."""
    rng = np.random.default_rng(seed)
    rows = []
    for tech, docs in spec.items():
        for doc, profile, n in docs:
            for k in rng.choice(len(profile), size=n, p=profile):
                rows.append({"technology_meta": tech, "source_file": doc, "cluster_id": int(k)})
    return pd.DataFrame(rows)


UNIFORM = np.full(4, 0.25)
# Cluster 3 only appears in technology A.
A_ONLY = np.array([0.2, 0.2, 0.2, 0.4])
NO_3 = np.array([1 / 3, 1 / 3, 1 / 3, 0.0])


class TestCoverage:
    def test_coverage_counts_technologies_at_half_mean(self):
        shares = pd.DataFrame([[0.5, 0.1], [0.5, 0.0], [0.5, 0.02]],
                              index=["A", "B", "C"], columns=[0, 1])
        cov = cc.coverage_counts(shares, level=0.5)
        # cluster 0: all equal -> 3; cluster 1: mean 0.04, bar 0.02 -> A and C
        assert list(cov) == [3, 2]

    def test_required_coverage(self):
        assert cc.required_coverage(12, 0.5) == 6
        assert cc.required_coverage(12, 0.4) == 5
        assert cc.required_coverage(12, 0.6) == 8
        assert cc.required_coverage(6, 0.5) == 3

    def test_size_of_technology_does_not_matter(self):
        # A is 10x bigger than the others; every cluster is spread evenly,
        # so all clusters should be cross-cutting regardless of A's size.
        spec = {"A": [(f"a{i}", UNIFORM, 500) for i in range(10)]}
        spec.update({t: [(f"{t}1", UNIFORM, 500)] for t in "BCDE"})
        clusters, s = cc.classify_crosscutting(_corpus(spec), 4, n_perm=0)
        assert clusters["cross_cutting"].all()
        assert s["n_technologies"] == 5


class TestClassification:
    def _spec(self):
        spec = {"A": [(f"a{i}", A_ONLY, 300) for i in range(4)]}
        spec.update({t: [(f"{t}{i}", NO_3, 300) for i in range(3)] for t in "BCDEF"})
        return spec

    def test_concentrated_cluster_flagged(self):
        clusters, s = cc.classify_crosscutting(_corpus(self._spec()), 4, n_perm=0)
        flags = dict(zip(clusters.cluster_id, clusters.cross_cutting))
        assert flags == {0: True, 1: True, 2: True, 3: False}
        assert clusters.loc[3, "coverage"] == 1
        assert clusters.loc[3, "top_technology"] == "A"

    def test_shuffling_test_outputs(self):
        clusters, s = cc.classify_crosscutting(_corpus(self._spec()), 4, n_perm=200)
        assert {"concentration_p", "concentration_q", "shuffled_mean_coverage"} <= set(clusters)
        # Cluster 3 is concentrated in one technology's documents: shuffling the
        # labels spreads those documents across technologies, so p is small.
        assert clusters.loc[3, "concentration_p"] < 0.05
        assert 0 < s["p_coverage_lower_than_shuffled"] <= 1
        assert "shuffled_median_coverage_95" in s

    def test_min_docs_filter_drops_small_technologies(self):
        spec = self._spec()
        spec["G"] = [("g1", UNIFORM, 300)]          # single-document technology
        _, s1 = cc.classify_crosscutting(_corpus(spec), 4, n_perm=0)
        _, s3 = cc.classify_crosscutting(_corpus(spec), 4, n_perm=0, min_docs_per_tech=3)
        assert "G" in s1["technologies"] and "G" not in s3["technologies"]

    def test_sensitivity_table(self):
        out = cc.crosscut_sensitivity(_corpus(self._spec()), 4, n_perm=20)
        assert len(out) == 3 * 3 * 2
        assert {"level", "min_fraction", "min_docs_per_tech", "cross_cutting"} <= set(out)


class TestSave:
    def test_writes_files_downstream_expects(self, tmp_path):
        clusters, s = cc.classify_crosscutting(
            _corpus({"A": [("a", A_ONLY, 300)], "B": [("b", NO_3, 300)]}), 4, n_perm=0)
        cc.save_crosscutting(clusters, s, tmp_path, "concern",
                             entropy_raw={0: 0.1}, entropy_norm={0: 0.2})
        data = json.loads((tmp_path / "cluster_entropy.json").read_text())
        assert set(data) >= {"raw", "norm", "cross_cutting", "method"}
        assert data["method"] == "coverage"
        assert (tmp_path / "cluster_crosscutting_concern.csv").exists()
        cc.save_crosscutting(clusters, s, tmp_path, "benefit")
        assert (tmp_path / "benefit_cluster_entropy.json").exists()

    def test_load_artifacts_reads_new_json(self, tmp_path):
        # load_artifacts expects raw/norm/cross_cutting keys — still present.
        clusters, s = cc.classify_crosscutting(
            _corpus({"A": [("a", A_ONLY, 300)], "B": [("b", NO_3, 300)]}), 4, n_perm=0)
        cc.save_crosscutting(clusters, s, tmp_path, "concern",
                             entropy_raw={0: 0.1}, entropy_norm={0: 0.2})
        data = json.loads((tmp_path / "cluster_entropy.json").read_text())
        assert {int(k): v for k, v in data["raw"].items()} == {0: 0.1}
        assert isinstance(data["cross_cutting"], list)


class TestMultiverseR1:
    def test_r1_uses_coverage(self):
        from pub_dialogue.multiverse import ell_R1_cross_cutting_share
        spec = {"A": [(f"a{i}", A_ONLY, 300) for i in range(2)]}
        spec.update({t: [(f"{t}1", NO_3, 300)] for t in "BCD"})
        df = _corpus(spec)
        assert ell_R1_cross_cutting_share(df, 0.5, 4) == pytest.approx(0.75)
