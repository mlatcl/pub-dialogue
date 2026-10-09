"""Tests for pub_dialogue.distance (EMD + MDS + PERMANOVA/PERMDISP)."""

import numpy as np
import pandas as pd
import pytest

from pub_dialogue import distance as dd

ot = pytest.importorskip("ot", reason="POT not installed (pip install pot)")


def _phrases(doc_profiles, n_per_doc=200, seed=0):
    """Build a phrase table: each doc draws clusters from its own profile."""
    rng = np.random.default_rng(seed)
    rows = []
    for doc, profile in doc_profiles.items():
        for k in rng.choice(len(profile), size=n_per_doc, p=profile):
            rows.append({"source_file": doc, "cluster_id": int(k)})
    return pd.DataFrame(rows)


class TestDistributions:
    def test_rows_sum_to_one_and_small_docs_dropped(self):
        df = pd.DataFrame({"source_file": ["a"] * 60 + ["b"] * 10,
                           "cluster_id": [0] * 30 + [1] * 30 + [2] * 10})
        P, docs, n = dd.document_cluster_distributions(df, 3, min_phrases=50)
        assert docs == ["a"]
        assert np.allclose(P.sum(axis=1), 1)
        assert np.allclose(P[0], [0.5, 0.5, 0.0])


class TestGroundCostAndEMD:
    def test_ground_cost_properties(self):
        C = np.random.default_rng(1).normal(size=(5, 8))
        M = dd.cosine_ground_cost(C)
        assert np.allclose(np.diag(M), 0)
        assert np.allclose(M, M.T)
        assert (M >= 0).all()

    def test_emd_known_value(self):
        # All mass moves from cluster 0 to cluster 1 at cost 0.3.
        M = np.array([[0.0, 0.3], [0.3, 0.0]])
        D = dd.emd_distance_matrix(np.array([[1.0, 0.0], [0.0, 1.0]]), M)
        assert D[0, 1] == pytest.approx(0.3)

    def test_emd_cheap_between_similar_clusters(self):
        # Moving mass between near-identical clusters (cost 0.05) is cheaper
        # than between distant ones (cost 0.9).
        M = np.array([[0, 0.05, 0.9], [0.05, 0, 0.9], [0.9, 0.9, 0]])
        P = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1.0]])
        D = dd.emd_distance_matrix(P, M)
        assert D[0, 1] < D[0, 2]
        assert np.allclose(D, D.T) and np.allclose(np.diag(D), 0)


class TestClassicalMDS:
    def test_recovers_euclidean_configuration(self):
        X = np.random.default_rng(2).normal(size=(20, 2))
        D = np.linalg.norm(X[:, None] - X[None], axis=2)
        res = dd.classical_mds(D, 2)
        D_hat = np.linalg.norm(res["coords"][:, None] - res["coords"][None], axis=2)
        assert np.allclose(D, D_hat, atol=1e-8)
        assert res["negative_ratio"] < 1e-8
        assert res["explained"].sum() == pytest.approx(1.0)


class TestPermanova:
    def _two_groups(self, separated):
        rng = np.random.default_rng(3)
        shift = 3.0 if separated else 0.0
        X = np.vstack([rng.normal(0, 1, (15, 3)), rng.normal(shift, 1, (15, 3))])
        D = np.linalg.norm(X[:, None] - X[None], axis=2)
        return D, np.array(["A"] * 15 + ["B"] * 15)

    def test_detects_location_difference(self):
        D, g = self._two_groups(separated=True)
        res = dd.permanova(D, g, n_perm=499)
        assert res["p_value"] < 0.01
        assert 0 < res["R2"] < 1

    def test_no_difference_gives_large_p(self):
        D, g = self._two_groups(separated=False)
        assert dd.permanova(D, g, n_perm=499)["p_value"] > 0.05

    def test_permdisp_detects_spread_difference(self):
        rng = np.random.default_rng(4)
        X = np.vstack([rng.normal(0, 0.2, (20, 3)), rng.normal(0, 2.0, (20, 3))])
        D = np.linalg.norm(X[:, None] - X[None], axis=2)
        g = np.array(["tight"] * 20 + ["loose"] * 20)
        res = dd.permdisp(D, g, n_perm=499)
        assert res["p_value"] < 0.01
        assert res["mean_distance_to_centroid"]["tight"] < res["mean_distance_to_centroid"]["loose"]

    def test_pairwise_has_one_row_per_pair(self):
        D, g = self._two_groups(separated=True)
        g = np.array(["A"] * 10 + ["B"] * 10 + ["C"] * 10)
        out = dd.pairwise_permanova(D, g, n_perm=99)
        assert list(out["comparison"]) == ["A vs B", "A vs C", "B vs C"]
        assert {"dispersion_p", "p_bonferroni", "spread_first"} <= set(out.columns)


class TestWrapper:
    def test_end_to_end_separates_groups(self):
        k = 6
        rng = np.random.default_rng(5)
        centroids = rng.normal(size=(k, 16))
        prof_a = np.array([0.4, 0.4, 0.05, 0.05, 0.05, 0.05])
        prof_b = np.array([0.05, 0.05, 0.05, 0.05, 0.4, 0.4])
        docs = {f"a{i}.pdf": prof_a for i in range(8)}
        docs.update({f"b{i}.pdf": prof_b for i in range(8)})
        docs["tiny.pdf"] = prof_a
        df = _phrases(docs)
        df = df[~((df.source_file == "tiny.pdf") & (df.index % 10 != 0))]  # ~20 phrases
        group = {d: ("A" if d.startswith("a") or d == "tiny.pdf" else "B") for d in docs}
        res = dd.run_document_distance_analysis(df, centroids, group,
                                                min_phrases=50, n_perm=199)
        assert "tiny.pdf" in res["dropped_docs"]
        assert len(res["docs"]) == 16
        assert res["permanova"]["p_value"] < 0.05
        assert res["mds"]["coords"].shape == (16, 2)
        assert set(res["axes"]["axis"]) == {1, 2}
