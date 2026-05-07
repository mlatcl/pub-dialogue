"""
tests/test_dialogue_utils.py — pytest test suite for dialogue_utils.py

Test categories:
  Pure utility functions  (no mocking needed)
  ExtractionResult dataclass
  Checkpoint I/O
  Extraction (mocked OpenAI client)
  Cluster labelling (mocked OpenAI client)
  Embeddings (mocked OpenAI client)
  Sensitivity output paths (mocked KMeans + minimal data)
  Comparison helpers
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import dialogue_utils as du


# ===========================================================================
# Pure utility functions
# ===========================================================================

class TestNormalizedEntropy:
    def test_uniform_two_elements(self):
        assert du.normalized_entropy([1, 1]) == pytest.approx(1.0)

    def test_uniform_four_elements(self):
        assert du.normalized_entropy([10, 10, 10, 10]) == pytest.approx(1.0)

    def test_concentrated(self):
        assert du.normalized_entropy([100, 0, 0, 0]) == pytest.approx(0.0)

    def test_single_element(self):
        assert du.normalized_entropy([42]) == 0.0

    def test_empty_after_filtering_zeros(self):
        assert du.normalized_entropy([0, 0, 0]) == 0.0

    def test_intermediate(self):
        result = du.normalized_entropy([3, 1])
        assert 0.0 < result < 1.0

    def test_returns_float(self):
        assert isinstance(du.normalized_entropy([1, 2, 3]), float)


class TestHHI:
    def test_monopoly(self):
        assert du.hhi([1, 0, 0]) == pytest.approx(1.0)

    def test_equal_two(self):
        assert du.hhi([1, 1]) == pytest.approx(0.5)

    def test_equal_four(self):
        assert du.hhi([1, 1, 1, 1]) == pytest.approx(0.25)

    def test_zero_sum_returns_nan(self):
        assert np.isnan(du.hhi([0, 0, 0]))

    def test_returns_float(self):
        assert isinstance(du.hhi([1, 2, 3]), float)


class TestTopkShare:
    def test_all_in_top_k(self):
        assert du.topk_share([1, 1, 1], k=5) == pytest.approx(1.0)

    def test_top1_of_three(self):
        result = du.topk_share([6, 2, 2], k=1)
        assert result == pytest.approx(0.6)

    def test_zero_sum_returns_nan(self):
        assert np.isnan(du.topk_share([0, 0], k=1))

    def test_returns_float(self):
        assert isinstance(du.topk_share([1, 2, 3], k=2), float)


class TestParseYear:
    def test_plain_integer(self):
        assert du.parse_year(2019) == 2019

    def test_string_integer(self):
        assert du.parse_year("2019") == 2019

    def test_embedded_year(self):
        assert du.parse_year("Report 2021-04") == 2021

    def test_invalid_returns_none(self):
        assert du.parse_year("n/a") is None

    def test_out_of_range_returns_none(self):
        assert du.parse_year("1800") is None
        assert du.parse_year("2200") is None

    def test_boundary_values(self):
        assert du.parse_year("1900") == 1900
        assert du.parse_year("2100") == 2100

    def test_nan_returns_none(self):
        assert du.parse_year(float("nan")) is None


class TestTokenize:
    def test_basic(self):
        assert du.tokenize("Hello world") == ["hello", "world"]

    def test_strips_punctuation(self):
        assert du.tokenize("Hello, world!") == ["hello", "world"]

    def test_min_length_4(self):
        result = du.tokenize("the AI and robots")
        # 'the' (3) and 'and' (3) filtered; 'robots' (6) kept
        assert "the" not in result
        assert "and" not in result
        assert "robots" in result

    def test_lowercases(self):
        result = du.tokenize("PRIVACY Risks")
        assert "privacy" in result
        assert "risks" in result

    def test_empty_string(self):
        assert du.tokenize("") == []


class TestIsPrivacyText:
    def test_matches_privacy(self):
        assert du.is_privacy_text("concerns about privacy") is True

    def test_matches_surveillance(self):
        assert du.is_privacy_text("government surveillance of citizens") is True

    def test_matches_gdpr(self):
        assert du.is_privacy_text("GDPR compliance required") is True

    def test_no_match(self):
        assert du.is_privacy_text("economic benefits of automation") is False

    def test_case_insensitive(self):
        assert du.is_privacy_text("PRIVACY concerns") is True


# ===========================================================================
# ExtractionResult dataclass
# ===========================================================================

class TestExtractionResult:
    def test_construction_defaults(self):
        r = du.ExtractionResult(chunk_id="c001")
        assert r.chunk_id == "c001"
        assert r.raw_phrases == []
        assert r.retained_phrases == []
        assert r.dropped_by_filter == []
        assert r.sentinel_returned is False
        assert r.error is None

    def test_filter_tracking(self):
        r = du.ExtractionResult(
            chunk_id="c002",
            raw_phrases=["concerns about artificial intelligence", "privacy risks"],
            retained_phrases=["privacy risks"],
            dropped_by_filter=[("concerns about artificial intelligence", "ai")],
            sentinel_returned=False,
        )
        assert len(r.dropped_by_filter) == 1
        assert r.dropped_by_filter[0][0] == "concerns about artificial intelligence"
        assert r.retained_phrases == ["privacy risks"]

    def test_sentinel_result(self):
        r = du.ExtractionResult(chunk_id="c003", sentinel_returned=True)
        assert r.sentinel_returned is True
        assert r.retained_phrases == []

    def test_error_result(self):
        r = du.ExtractionResult(chunk_id="c004", error="ConnectionError: timeout")
        assert r.error is not None
        assert "timeout" in r.error
        assert r.retained_phrases == []


# ===========================================================================
# write_extraction_diagnostics
# ===========================================================================

class TestWriteExtractionDiagnostics:
    """Tests for the CIP-0001 diagnostic file writer."""

    def _make_results(self):
        return [
            du.ExtractionResult(
                chunk_id="c001",
                raw_phrases=["privacy risks", "AI surveillance"],
                retained_phrases=["privacy risks"],
                dropped_by_filter=[("AI surveillance", "ai")],
            ),
            du.ExtractionResult(
                chunk_id="c002",
                sentinel_returned=True,
            ),
            du.ExtractionResult(
                chunk_id="c003",
                raw_phrases=["job displacement"],
                retained_phrases=["job displacement"],
            ),
            du.ExtractionResult(
                chunk_id="c004",
                error="TimeoutError: request timed out",
            ),
        ]

    def test_yield_summary_csv_created(self, tmp_path):
        results = self._make_results()
        du.write_extraction_diagnostics(results, kind="concern", output_folder=tmp_path)
        summary = tmp_path / "extraction_yield_summary.csv"
        assert summary.exists()
        df = pd.read_csv(summary)
        assert len(df) == 1
        row = df.iloc[0]
        assert row["track"] == "concern"
        assert row["total_chunks"] == 4
        assert row["sentinel_empties"] == 1
        assert row["error_chunks"] == 1
        assert row["filter_drops_chunks"] == 1
        assert row["filter_drops_total"] == 1
        assert row["retained_phrases"] == 2

    def test_filter_drops_csv_created(self, tmp_path):
        results = self._make_results()
        du.write_extraction_diagnostics(results, kind="concern", output_folder=tmp_path)
        drops = tmp_path / "tech_filter_drops_concern.csv"
        assert drops.exists()
        df = pd.read_csv(drops)
        assert len(df) == 1
        assert df.iloc[0]["dropped_phrase"] == "AI surveillance"
        assert df.iloc[0]["matching_tech_word"] == "ai"
        assert df.iloc[0]["chunk_id"] == "c001"

    def test_errors_csv_created(self, tmp_path):
        results = self._make_results()
        du.write_extraction_diagnostics(results, kind="concern", output_folder=tmp_path)
        errors = tmp_path / "extraction_errors_concern.csv"
        assert errors.exists()
        df = pd.read_csv(errors)
        assert len(df) == 1
        assert df.iloc[0]["chunk_id"] == "c004"
        assert "TimeoutError" in df.iloc[0]["error"]

    def test_benefit_kind_uses_separate_files(self, tmp_path):
        results = [du.ExtractionResult(chunk_id="b001", retained_phrases=["efficiency gains"])]
        du.write_extraction_diagnostics(results, kind="benefit", output_folder=tmp_path)
        assert (tmp_path / "tech_filter_drops_benefit.csv").exists()
        assert (tmp_path / "extraction_errors_benefit.csv").exists()
        df = pd.read_csv(tmp_path / "extraction_yield_summary.csv")
        assert df.iloc[0]["track"] == "benefit"

    def test_summary_appends_second_track(self, tmp_path):
        concern_results = [du.ExtractionResult(chunk_id="c001", retained_phrases=["risk"])]
        benefit_results = [du.ExtractionResult(chunk_id="b001", retained_phrases=["gain"])]
        du.write_extraction_diagnostics(concern_results, kind="concern", output_folder=tmp_path)
        du.write_extraction_diagnostics(benefit_results, kind="benefit", output_folder=tmp_path)
        df = pd.read_csv(tmp_path / "extraction_yield_summary.csv")
        assert len(df) == 2
        assert set(df["track"]) == {"concern", "benefit"}

    def test_summary_replaces_same_track_on_rerun(self, tmp_path):
        results1 = [du.ExtractionResult(chunk_id="c001", retained_phrases=["risk"])]
        results2 = [
            du.ExtractionResult(chunk_id="c001", retained_phrases=["risk"]),
            du.ExtractionResult(chunk_id="c002", retained_phrases=["job loss"]),
        ]
        du.write_extraction_diagnostics(results1, kind="concern", output_folder=tmp_path)
        du.write_extraction_diagnostics(results2, kind="concern", output_folder=tmp_path)
        df = pd.read_csv(tmp_path / "extraction_yield_summary.csv")
        assert len(df) == 1  # same track, replaced not appended
        assert df.iloc[0]["total_chunks"] == 2

    def test_empty_results_writes_zero_row(self, tmp_path):
        du.write_extraction_diagnostics([], kind="concern", output_folder=tmp_path)
        df = pd.read_csv(tmp_path / "extraction_yield_summary.csv")
        assert df.iloc[0]["total_chunks"] == 0
        assert df.iloc[0]["retained_phrases"] == 0


# ===========================================================================
# vocabulary_frequency_diagnostic — CIP-0004
# ===========================================================================

class TestVocabularyFrequencyDiagnostic:
    """Tests for the CIP-0004 vocabulary frequency diagnostic."""

    def _sample_phrases(self):
        return [
            "public dialogue concerns about safety",
            "public dialogue lack of transparency",
            "unfair automated decisions",
            "loss of employment opportunities",
            "public dialogue process not inclusive",
            "data privacy risks",
            "public engagement inadequate",
            "risk of job displacement",
        ]

    def test_csv_created(self, tmp_path):
        du.vocabulary_frequency_diagnostic(
            self._sample_phrases(), kind="concern", output_folder=tmp_path
        )
        assert (tmp_path / "concern_vocab_frequency.csv").exists()

    def test_returns_dataframe(self, tmp_path):
        df = du.vocabulary_frequency_diagnostic(
            self._sample_phrases(), kind="concern", output_folder=tmp_path
        )
        assert isinstance(df, pd.DataFrame)
        assert "term" in df.columns
        assert "count" in df.columns
        assert "pct_of_phrases" in df.columns
        assert "is_meta_vocab" in df.columns

    def test_meta_vocab_flagged(self, tmp_path):
        df = du.vocabulary_frequency_diagnostic(
            self._sample_phrases(), kind="concern", output_folder=tmp_path
        )
        flagged = df[df["is_meta_vocab"]]
        assert not flagged.empty
        flagged_terms = set(flagged["term"].tolist())
        assert "public dialogue" in flagged_terms

    def test_non_meta_vocab_not_flagged(self, tmp_path):
        df = du.vocabulary_frequency_diagnostic(
            self._sample_phrases(), kind="concern", output_folder=tmp_path
        )
        # "unfair" is not a meta-vocab term — check is_meta_vocab is False where it appears
        row = df[df["term"] == "unfair"]
        if not row.empty:
            assert bool(row.iloc[0]["is_meta_vocab"]) is False

    def test_benefit_kind_filename(self, tmp_path):
        du.vocabulary_frequency_diagnostic(
            ["efficiency gains", "cost savings"], kind="benefit", output_folder=tmp_path
        )
        assert (tmp_path / "benefit_vocab_frequency.csv").exists()

    def test_top_n_respected(self, tmp_path):
        phrases = [f"concern about topic {i}" for i in range(50)]
        df = du.vocabulary_frequency_diagnostic(
            phrases, kind="concern", output_folder=tmp_path, top_n=10
        )
        assert len(df) <= 10

    def test_bigrams_included(self, tmp_path):
        df = du.vocabulary_frequency_diagnostic(
            self._sample_phrases(), kind="concern", output_folder=tmp_path
        )
        terms = df["term"].tolist()
        # "public dialogue" is a bigram and should appear
        assert "public dialogue" in terms

    def test_pct_of_phrases_sane(self, tmp_path):
        df = du.vocabulary_frequency_diagnostic(
            self._sample_phrases(), kind="concern", output_folder=tmp_path
        )
        assert (df["pct_of_phrases"] >= 0).all()
        assert (df["pct_of_phrases"] <= 100).all()

    def test_empty_phrases_no_crash(self, tmp_path):
        df = du.vocabulary_frequency_diagnostic(
            [], kind="concern", output_folder=tmp_path
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_custom_meta_vocabulary(self, tmp_path):
        custom = ["job displacement"]
        df = du.vocabulary_frequency_diagnostic(
            ["risk of job displacement", "unfair automated decisions"],
            kind="concern",
            output_folder=tmp_path,
            meta_vocabulary=custom,
        )
        flagged = df[df["is_meta_vocab"]]
        flagged_terms = set(flagged["term"].tolist())
        assert "job displacement" in flagged_terms
        assert "public dialogue" not in flagged_terms


# ===========================================================================
# Checkpoint I/O
# ===========================================================================

class TestCheckpoints:
    def test_roundtrip_dict(self, tmp_path):
        data = {"key": [1, 2, 3], "nested": {"a": "b"}}
        path = tmp_path / "ckpt.json"
        du.save_checkpoint(data, path)
        loaded = du.load_checkpoint(path)
        assert loaded == data

    def test_roundtrip_list(self, tmp_path):
        data = ["apple", "banana", "cherry"]
        path = tmp_path / "list_ckpt.json"
        du.save_checkpoint(data, path)
        assert du.load_checkpoint(path) == data

    def test_missing_file_returns_none(self, tmp_path):
        assert du.load_checkpoint(tmp_path / "nonexistent.json") is None

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "subdir" / "deep" / "ckpt.json"
        du.save_checkpoint({"x": 1}, path)
        assert path.exists()

    def test_returns_path(self, tmp_path):
        path = tmp_path / "ckpt.json"
        result = du.save_checkpoint({}, path)
        assert result == path


# ===========================================================================
# Extraction — mocked OpenAI client
# ===========================================================================

def _make_response(content: str):
    """Build a minimal mock OpenAI chat completion response."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_row(chunk_id: str = "c001", text: str = "Some paragraph text."):
    import pandas as pd
    row = pd.Series({"chunk_id": chunk_id, "text": text})
    return (0, row)


class TestExtractPhrases:
    def test_concern_normal_extraction(self):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_response(
            "job loss risk\nworkplace automation anxiety"
        )
        result = du.extract_phrases(_make_row(), kind="concern", client=client)
        assert isinstance(result, du.ExtractionResult)
        assert result.sentinel_returned is False
        assert result.error is None
        assert "job loss risk" in result.retained_phrases

    def test_benefit_normal_extraction(self):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_response(
            "faster medical diagnosis"
        )
        result = du.extract_phrases(_make_row(), kind="benefit", client=client)
        assert "faster medical diagnosis" in result.retained_phrases
        assert result.sentinel_returned is False

    def test_sentinel_concern_returns_empty(self):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_response("NO_CONCERN")
        result = du.extract_phrases(_make_row(), kind="concern", client=client)
        assert result.sentinel_returned is True
        assert result.retained_phrases == []

    def test_sentinel_benefit_returns_empty(self):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_response("NO_BENEFIT")
        result = du.extract_phrases(_make_row(), kind="benefit", client=client)
        assert result.sentinel_returned is True

    def test_tech_word_filter_drops_phrase(self):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_response(
            "concerns about ai systems\nprivacy risks"
        )
        result = du.extract_phrases(
            _make_row(), kind="concern", client=client,
            tech_words=["ai"]
        )
        assert "privacy risks" in result.retained_phrases
        assert any("ai" in drop[1] for drop in result.dropped_by_filter)

    def test_api_error_captured(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = ConnectionError("timeout")
        result = du.extract_phrases(_make_row(), kind="concern", client=client)
        assert result.error is not None
        assert "timeout" in result.error
        assert result.retained_phrases == []

    def test_invalid_kind_raises(self):
        client = MagicMock()
        with pytest.raises(ValueError, match="kind must be"):
            du.extract_phrases(_make_row(), kind="question", client=client)

    def test_raw_phrases_populated(self):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_response(
            "privacy risks\nconcerns about artificial intelligence"
        )
        result = du.extract_phrases(
            _make_row(), kind="concern", client=client,
            tech_words=["artificial intelligence"]
        )
        assert len(result.raw_phrases) == 2
        assert len(result.retained_phrases) == 1
        assert len(result.dropped_by_filter) == 1


# ===========================================================================
# Cluster labelling — mocked OpenAI client
# ===========================================================================

class TestLabelCluster:
    def _exemplars(self, kind="concern"):
        key = kind
        return [
            {key: "job loss risk", "technology": "AI"},
            {key: "workplace disruption", "technology": "Nuclear"},
        ]

    def test_concern_labelling(self):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_response(
            '{"label": "Employment displacement", "description": "Fear of job losses.", "key_terms": ["jobs", "automation"]}'
        )
        result = du.label_cluster(1, self._exemplars("concern"), True, kind="concern", client=client)
        assert result["success"] is True
        assert result["label"] == "Employment displacement"

    def test_benefit_labelling(self):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_response(
            '{"label": "Faster healthcare", "description": "Improved diagnostics.", "key_terms": ["health", "speed"]}'
        )
        result = du.label_cluster(2, self._exemplars("benefit"), False, kind="benefit", client=client)
        assert result["success"] is True
        assert result["label"] == "Faster healthcare"

    def test_api_error_returns_fallback(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("API error")
        result = du.label_cluster(99, self._exemplars(), True, kind="concern", client=client)
        assert result["success"] is False
        assert "Cluster 99" in result["label"]

    def test_no_client_returns_fallback(self):
        result = du.label_cluster(5, self._exemplars(), False, kind="concern", client=None)
        assert result["success"] is False

    def test_invalid_kind_raises(self):
        with pytest.raises(ValueError):
            du.label_cluster(1, [], False, kind="topic", client=None)


# ===========================================================================
# Embeddings — mocked OpenAI client
# ===========================================================================

class TestGetEmbeddingsBatch:
    def test_returns_numpy_array(self):
        client = MagicMock()
        fake_item = MagicMock()
        fake_item.embedding = [0.1, 0.2, 0.3]
        client.embeddings.create.return_value = MagicMock(data=[fake_item, fake_item])
        result = du.get_embeddings_batch(["hello", "world"], client=client)
        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 3)

    def test_correct_model_passed(self):
        client = MagicMock()
        fake_item = MagicMock()
        fake_item.embedding = [0.0]
        client.embeddings.create.return_value = MagicMock(data=[fake_item])
        du.get_embeddings_batch(["text"], client=client, model="text-embedding-3-large")
        call_kwargs = client.embeddings.create.call_args[1]
        assert call_kwargs["model"] == "text-embedding-3-large"


# ===========================================================================
# Sensitivity output paths — mocked KMeans
# ===========================================================================

class TestRunSensitivity:
    def _make_df(self, n: int = 20):
        """Minimal dataframe mimicking concerns_df / benefits_df."""
        rng = np.random.default_rng(0)
        return pd.DataFrame({
            "cluster_id": rng.integers(0, 3, size=n),
            "technology_meta": rng.choice(["AI", "Nuclear", "Genetic"], size=n),
            "year": rng.choice([2015, 2018, 2021], size=n),
            "concern": [f"phrase {i}" for i in range(n)],
            "benefit": [f"benefit {i}" for i in range(n)],
        })

    def _make_embeddings(self, n: int = 20, dim: int = 4):
        rng = np.random.default_rng(0)
        X = rng.random((n, dim)).astype(np.float32)
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        return X / norms

    def test_concern_output_prefix(self, tmp_path):
        df = self._make_df()
        emb = self._make_embeddings()
        du.run_sensitivity(3, "concern", emb, df, tmp_path, random_seed=0)
        assert (tmp_path / "concern_sensitivity_stable_core_k3.csv").exists()
        assert not (tmp_path / "benefit_sensitivity_stable_core_k3.csv").exists()

    def test_benefit_output_prefix(self, tmp_path):
        df = self._make_df()
        emb = self._make_embeddings()
        du.run_sensitivity(3, "benefit", emb, df, tmp_path, random_seed=0)
        assert (tmp_path / "benefit_sensitivity_stable_core_k3.csv").exists()
        assert not (tmp_path / "concern_sensitivity_stable_core_k3.csv").exists()

    def test_both_tracks_independent(self, tmp_path):
        df = self._make_df()
        emb = self._make_embeddings()
        du.run_sensitivity(3, "concern", emb, df, tmp_path, random_seed=0)
        du.run_sensitivity(3, "benefit", emb, df, tmp_path, random_seed=0)
        assert (tmp_path / "concern_sensitivity_stable_core_k3.csv").exists()
        assert (tmp_path / "benefit_sensitivity_stable_core_k3.csv").exists()

    def test_stable_core_csv_columns(self, tmp_path):
        df = self._make_df()
        emb = self._make_embeddings()
        du.run_sensitivity(3, "concern", emb, df, tmp_path, random_seed=0)
        out = pd.read_csv(tmp_path / "concern_sensitivity_stable_core_k3.csv")
        assert "cluster_id_k" in out.columns
        assert "tech_entropy" in out.columns
        assert "global_prevalence" in out.columns
        assert len(out) == 3  # k=3

    def test_invalid_kind_raises(self, tmp_path):
        df = self._make_df()
        emb = self._make_embeddings()
        with pytest.raises(ValueError, match="kind must be"):
            du.run_sensitivity(3, "topic", emb, df, tmp_path)


# ===========================================================================
# Comparison helpers
# ===========================================================================

class TestVolumeTable:
    def _make_df(self):
        return pd.DataFrame({
            "technology": ["AI", "AI", "Nuclear"],
            "year": [2018, 2018, 2020],
            "chunk_id": ["c1", "c2", "c1"],
        })

    def test_returns_dataframe(self):
        result = du._volume_table(self._make_df(), "concern")
        assert isinstance(result, pd.DataFrame)

    def test_columns_named_by_kind(self):
        result = du._volume_table(self._make_df(), "concern")
        assert "concern_phrases" in result.columns

    def test_raises_without_id_column(self):
        df = pd.DataFrame({"technology": ["AI"], "year": [2020]})
        with pytest.raises(ValueError, match="paragraph id column"):
            du._volume_table(df, "concern")


class TestTopClusters:
    def _make_df(self):
        return pd.DataFrame({
            "cluster_id": [0, 0, 1, 2, 0, 1],
        })

    def test_returns_top_n(self):
        result = du._top_clusters(self._make_df(), None, "concern", n=2)
        assert len(result) == 2
        assert result.iloc[0]["cluster_id"] == 0  # most frequent

    def test_kind_column_inserted(self):
        result = du._top_clusters(self._make_df(), None, "benefit")
        assert "kind" in result.columns
        assert (result["kind"] == "benefit").all()

    def test_merges_labels(self):
        summary = pd.DataFrame({"cluster_id": [0, 1], "label": ["Alpha", "Beta"]})
        result = du._top_clusters(self._make_df(), summary, "concern")
        assert "label" in result.columns


# ===========================================================================
# pretty_label / clusters_to_labels / clusters_to_lenses
# ===========================================================================

class TestPrettyLabel:
    def test_truncates_long_label(self):
        labels = {1: "A" * 50}
        result = du.pretty_label(1, labels, max_len=40)
        assert result.endswith("...")
        assert len(result) <= 40

    def test_short_label_unchanged(self):
        labels = {1: "Short label"}
        assert du.pretty_label(1, labels) == "Short label"

    def test_missing_key_fallback(self):
        assert du.pretty_label(99, {}) == "Cluster 99"

    def test_none_labels_fallback(self):
        assert du.pretty_label(5, None) == "Cluster 5"


class TestClustersToLabels:
    def test_maps_ids(self):
        label_map = {0: "Alpha", 1: "Beta"}
        result = du.clusters_to_labels([0, 1], label_map)
        assert result == ["Alpha", "Beta"]

    def test_missing_id_fallback(self):
        result = du.clusters_to_labels([99], {})
        assert result == ["Cluster 99"]

    def test_non_list_returns_empty(self):
        assert du.clusters_to_labels(None, {}) == []


class TestClustersToLenses:
    def test_returns_sorted_lenses(self):
        mapping = {0: {"safety", "privacy"}, 1: {"privacy"}}
        result = du.clusters_to_lenses([0, 1], mapping)
        assert result == sorted(["safety", "privacy"])

    def test_non_list_returns_empty(self):
        assert du.clusters_to_lenses(None, {}) == []

    def test_unknown_cluster_ignored(self):
        result = du.clusters_to_lenses([99], {})
        assert result == []
