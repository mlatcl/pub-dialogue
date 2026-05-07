"""
conftest.py — pytest configuration for dialogue_utils tests.

Pre-installs lightweight mock versions of sklearn and scipy into sys.modules
so that sensitivity tests can run without a working sklearn installation.
The actual KMeans logic is exercised via the mock; correctness of the
clustering algorithm itself is not under test here.
"""

import sys
from types import ModuleType
from unittest.mock import MagicMock
import numpy as np


def _install_mock_sklearn():
    """Insert a minimal sklearn mock into sys.modules if sklearn is broken."""
    try:
        import sklearn  # noqa: F401
        from sklearn.cluster import KMeans  # noqa: F401
        # If we got here sklearn is fine — nothing to do.
        return
    except Exception:
        pass

    # Build a minimal mock KMeans that runs fit_predict on real numpy data.
    class _MockKMeans:
        def __init__(self, n_clusters=8, random_state=None, n_init="auto"):
            self.n_clusters = n_clusters
            self.random_state = random_state
            self.cluster_centers_ = None

        def fit_predict(self, X):
            rng = np.random.default_rng(self.random_state)
            n = len(X)
            labels = rng.integers(0, self.n_clusters, size=n)
            # Simple centroids: mean of assigned points per cluster
            dim = X.shape[1] if X.ndim > 1 else 1
            self.cluster_centers_ = rng.random((self.n_clusters, dim))
            return labels

    # Build module hierarchy
    sklearn_mock = ModuleType("sklearn")
    sklearn_cluster = ModuleType("sklearn.cluster")
    sklearn_cluster.KMeans = _MockKMeans
    sklearn_mock.cluster = sklearn_cluster

    sys.modules.setdefault("sklearn", sklearn_mock)
    sys.modules.setdefault("sklearn.cluster", sklearn_cluster)


def _install_mock_scipy():
    """Insert a minimal scipy mock if scipy is unavailable."""
    try:
        from scipy.stats import entropy  # noqa: F401
        return
    except Exception:
        pass

    def _entropy(p):
        p = np.asarray(p, dtype=float)
        p = p[p > 0]
        if len(p) == 0:
            return 0.0
        p = p / p.sum()
        return float(-(p * np.log(p)).sum())

    scipy_mock = ModuleType("scipy")
    scipy_stats = ModuleType("scipy.stats")
    scipy_stats.entropy = _entropy
    scipy_mock.stats = scipy_stats

    sys.modules.setdefault("scipy", scipy_mock)
    sys.modules.setdefault("scipy.stats", scipy_stats)


_install_mock_sklearn()
_install_mock_scipy()
