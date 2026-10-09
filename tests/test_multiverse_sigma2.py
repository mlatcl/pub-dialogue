"""Tests for the multiverse σ² selection rules.

The key guarantee: the multiverse's "constrained" rule picks exactly the σ²
that 01a's AddressStage.sigma2_sweep_select picks, so the multiverse's
canonical configuration reproduces the headline results.
"""

import numpy as np
import pandas as pd
import pytest

from pub_dialogue import multiverse as mv


def _curve(sigma2, eff, emd):
    return pd.DataFrame({"sigma2": sigma2, "mean_eff_support": eff, "mean_emd": emd})


# Shape of the real concern curve: EMD keeps falling as memberships become
# near-uniform, so the unconstrained minimum is the degenerate high-σ² end.
GRID = np.logspace(-4, 2, 25)
EFF = np.concatenate([np.linspace(1.0, 1.3, 10), [2.09, 4.52, 7.54],
                      np.linspace(9.25, 10.2, 12)])
EMD = np.concatenate([np.full(10, 0.064), [0.0596, 0.0572, 0.0555],
                      np.linspace(0.0554, 0.0549, 12)])
CURVE = _curve(GRID, EFF, EMD)
N_LENSES = 10.2


class TestRules:
    def test_constrained_avoids_degenerate_solution(self):
        s2 = mv.select_sigma2_constrained(CURVE, N_LENSES)
        assert s2 == pytest.approx(GRID[11])          # eff 4.52, inside (2.04, 6.12)
        assert mv.select_sigma2_min_emd(CURVE) > 0.3   # legacy rule: degenerate

    def test_neighbours_and_hard(self):
        assert mv.select_sigma2_one_step_harder(CURVE, N_LENSES) == pytest.approx(GRID[10])
        assert mv.select_sigma2_one_step_softer(CURVE, N_LENSES) == pytest.approx(GRID[12])
        assert mv.select_sigma2_hard(CURVE, N_LENSES) == pytest.approx(GRID[0])

    def test_band_is_open_interval_and_falls_back(self):
        # Nothing strictly inside the band -> unconstrained min-EMD row.
        c = _curve([0.1, 1.0], [2.04, 9.0], [0.2, 0.1])
        assert mv.select_sigma2_constrained(c, 10.2) == pytest.approx(1.0)

    def test_rule_names(self):
        assert list(mv.SIGMA2_RULES) == ["constrained", "one_step_harder",
                                         "one_step_softer", "hard"]
        assert mv.MultiverseConfig().sigma2_rule == "constrained"

    def test_unknown_rule_raises(self):
        bundle = {"per_run_mappings": [{"A": {"cluster_ids": [0]}}],
                  "stability_curve": CURVE}
        cfg = mv.MultiverseConfig(sigma2_rule="min_emd_support_cap")
        with pytest.raises(ValueError, match="Unknown sigma2_rule"):
            mv.run_configuration(cfg, bundle, lambda *a, **k: None)


class TestMatchesAddressSweep:
    """The multiverse's canonical rule must agree with 01a's selection."""

    @pytest.mark.parametrize("seed", [0, 1, 2])
    def test_constrained_equals_sigma2_sweep_select(self, seed):
        from pub_dialogue.access import AccessStage
        from pub_dialogue.address import AddressStage

        rng = np.random.default_rng(seed)
        k, dim = 30, 12
        centroids = rng.normal(size=(k, dim))
        centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)
        mappings = []
        for _ in range(3):
            perm = rng.permutation(k)
            mappings.append({f"L{j}": {"cluster_ids": perm[j::6].tolist()} for j in range(6)})

        address = AddressStage(access=AccessStage())
        res = address.sigma2_sweep_select(centroids, mappings)
        curve = pd.DataFrame(res["curve"])
        assert mv.select_sigma2_constrained(curve, mv.mean_n_lenses(mappings)) == \
            pytest.approx(res["sigma2_best"])
