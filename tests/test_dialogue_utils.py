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
from pub_dialogue.client import LLMClient

import numpy as np
import pandas as pd
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import pub_dialogue.utils as du


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
# generate_validation_summary — CIP-0005
# ===========================================================================

class TestGenerateValidationSummary:
    """Tests for the CIP-0005 validation summary generator."""

    def _write_yield_csv(self, tmp_path, concern_row, benefit_row=None):
        rows = [concern_row]
        if benefit_row:
            rows.append(benefit_row)
        pd.DataFrame(rows).to_csv(tmp_path / "extraction_yield_summary.csv", index=False)

    def _make_env(self, tmp_path):
        """Populate a minimal output folder with the files Activity 4 checks."""
        self._write_yield_csv(
            tmp_path,
            {"track": "concern", "total_chunks": 100, "retained_phrases": 80,
             "sentinel_empties": 10, "filter_drops_chunks": 5,
             "filter_drops_total": 8, "error_chunks": 5},
            {"track": "benefit", "total_chunks": 100, "retained_phrases": 60,
             "sentinel_empties": 20, "filter_drops_chunks": 3,
             "filter_drops_total": 4, "error_chunks": 2},
        )
        pd.DataFrame([{"chunk_id": f"c{i}", "text": "text"} for i in range(100)]).to_csv(
            tmp_path / "paragraph_chunks.csv", index=False
        )
        pd.DataFrame([{"chunk_id": "c0", "concern": "risk"}] * 80).to_csv(
            tmp_path / "extracted_concerns.csv", index=False
        )
        pd.DataFrame([{"chunk_id": "c0", "benefit": "gain"}] * 60).to_csv(
            tmp_path / "extracted_benefits.csv", index=False
        )
        pd.DataFrame([{"cluster_id": i, "label": f"l{i}"} for i in range(75)]).to_csv(
            tmp_path / "cluster_summary.csv", index=False
        )

    def test_file_created(self, tmp_path):
        self._make_env(tmp_path)
        path = du.generate_validation_summary(tmp_path)
        assert path.exists()
        assert path.name == "validation_summary.txt"

    def test_returns_path(self, tmp_path):
        self._make_env(tmp_path)
        result = du.generate_validation_summary(tmp_path)
        assert isinstance(result, Path)

    def test_contains_concern_counts(self, tmp_path):
        self._make_env(tmp_path)
        du.generate_validation_summary(tmp_path)
        content = (tmp_path / "validation_summary.txt").read_text()
        assert "80" in content   # retained phrases
        assert "CONCERNS" in content

    def test_contains_benefit_counts(self, tmp_path):
        self._make_env(tmp_path)
        du.generate_validation_summary(tmp_path)
        content = (tmp_path / "validation_summary.txt").read_text()
        assert "BENEFITS" in content
        assert "60" in content   # retained benefit phrases

    def test_cluster_count_ok(self, tmp_path):
        self._make_env(tmp_path)
        du.generate_validation_summary(tmp_path, n_concern_clusters=75)
        content = (tmp_path / "validation_summary.txt").read_text()
        assert "[OK]" in content

    def test_cluster_count_mismatch(self, tmp_path):
        self._make_env(tmp_path)
        du.generate_validation_summary(tmp_path, n_concern_clusters=90)
        content = (tmp_path / "validation_summary.txt").read_text()
        assert "MISMATCH" in content

    def test_missing_file_flagged(self, tmp_path):
        self._make_env(tmp_path)
        du.generate_validation_summary(tmp_path)
        content = (tmp_path / "validation_summary.txt").read_text()
        # cluster_exemplars.json was not created in _make_env
        assert "[MISSING]" in content
        assert "cluster_exemplars.json" in content

    def test_no_crash_on_empty_folder(self, tmp_path):
        path = du.generate_validation_summary(tmp_path)
        assert path.exists()
        content = path.read_text()
        assert "FILE NOT FOUND" in content or "MISSING" in content


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
# Extraction — mocked LLMClient
# ===========================================================================

def _make_row(chunk_id: str = "c001", text: str = "Some paragraph text."):
    import pandas as pd
    row = pd.Series({"chunk_id": chunk_id, "text": text})
    return (0, row)


def _mock_client(complete_return: str = "") -> MagicMock:
    """Return a MagicMock(spec=LLMClient) with complete() pre-configured."""
    client = MagicMock(spec=LLMClient)
    client.complete.return_value = complete_return
    return client


class TestExtractPhrases:
    def test_concern_normal_extraction(self):
        client = _mock_client("job loss risk\nworkplace automation anxiety")
        result = du.extract_phrases(_make_row(), kind="concern", client=client)
        assert isinstance(result, du.ExtractionResult)
        assert result.sentinel_returned is False
        assert result.error is None
        assert "job loss risk" in result.retained_phrases

    def test_benefit_normal_extraction(self):
        client = _mock_client("faster medical diagnosis")
        result = du.extract_phrases(_make_row(), kind="benefit", client=client)
        assert "faster medical diagnosis" in result.retained_phrases
        assert result.sentinel_returned is False

    def test_sentinel_concern_returns_empty(self):
        client = _mock_client("NO_CONCERN")
        result = du.extract_phrases(_make_row(), kind="concern", client=client)
        assert result.sentinel_returned is True
        assert result.retained_phrases == []

    def test_sentinel_benefit_returns_empty(self):
        client = _mock_client("NO_BENEFIT")
        result = du.extract_phrases(_make_row(), kind="benefit", client=client)
        assert result.sentinel_returned is True

    def test_tech_word_filter_drops_phrase(self):
        client = _mock_client("concerns about ai systems\nprivacy risks")
        result = du.extract_phrases(
            _make_row(), kind="concern", client=client,
            tech_words=["ai"]
        )
        assert "privacy risks" in result.retained_phrases
        assert any("ai" in drop[1] for drop in result.dropped_by_filter)

    def test_api_error_captured(self):
        client = MagicMock(spec=LLMClient)
        client.complete.side_effect = ConnectionError("timeout")
        result = du.extract_phrases(_make_row(), kind="concern", client=client)
        assert result.error is not None
        assert "timeout" in result.error
        assert result.retained_phrases == []

    def test_invalid_kind_raises(self):
        client = _mock_client()
        with pytest.raises(ValueError, match="kind must be"):
            du.extract_phrases(_make_row(), kind="question", client=client)

    def test_raw_phrases_populated(self):
        client = _mock_client("privacy risks\nconcerns about artificial intelligence")
        result = du.extract_phrases(
            _make_row(), kind="concern", client=client,
            tech_words=["artificial intelligence"]
        )
        assert len(result.raw_phrases) == 2
        assert len(result.retained_phrases) == 1
        assert len(result.dropped_by_filter) == 1


# ===========================================================================
# Cluster labelling — mocked LLMClient
# ===========================================================================

class TestLabelCluster:
    def _exemplars(self, kind="concern"):
        key = kind
        return [
            {key: "job loss risk", "technology": "AI"},
            {key: "workplace disruption", "technology": "Nuclear"},
        ]

    def test_concern_labelling(self):
        client = _mock_client(
            '{"label": "Employment displacement", "description": "Fear of job losses.", "key_terms": ["jobs", "automation"]}'
        )
        result = du.label_cluster(1, self._exemplars("concern"), True, kind="concern", client=client)
        assert result["success"] is True
        assert result["label"] == "Employment displacement"

    def test_benefit_labelling(self):
        client = _mock_client(
            '{"label": "Faster healthcare", "description": "Improved diagnostics.", "key_terms": ["health", "speed"]}'
        )
        result = du.label_cluster(2, self._exemplars("benefit"), False, kind="benefit", client=client)
        assert result["success"] is True
        assert result["label"] == "Faster healthcare"

    def test_api_error_returns_fallback(self):
        client = MagicMock(spec=LLMClient)
        client.complete.side_effect = Exception("API error")
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
# Embeddings — mocked LLMClient
# ===========================================================================

class TestGetEmbeddingsBatch:
    def test_returns_numpy_array(self):
        client = MagicMock(spec=LLMClient)
        client.embed.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        result = du.get_embeddings_batch(["hello", "world"], client=client)
        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 3)

    def test_embed_called_with_texts(self):
        client = MagicMock(spec=LLMClient)
        client.embed.return_value = [[0.0]]
        du.get_embeddings_batch(["text"], client=client)
        client.embed.assert_called_once_with(["text"])


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


# ===========================================================================
# CIP-0006: validate_extraction_cache
# ===========================================================================

class TestValidateExtractionCache:
    def test_healthy_cache_returns_true(self):
        cache = {"id1": ["phrase a"], "id2": ["phrase b", "phrase c"]}
        assert du.validate_extraction_cache(cache, "concern") is True

    def test_empty_cache_returns_false(self):
        assert du.validate_extraction_cache({}, "concern") is False

    def test_all_empty_entries_returns_false(self, capsys):
        cache = {"id1": [], "id2": [], "id3": []}
        result = du.validate_extraction_cache(cache, "concern")
        assert result is False
        captured = capsys.readouterr()
        assert "WARN" in captured.out

    def test_below_threshold_returns_true(self):
        cache = {"id1": [], "id2": ["phrase"], "id3": ["phrase"], "id4": ["phrase"]}
        assert du.validate_extraction_cache(cache, "concern") is True

    def test_above_threshold_prints_warning(self, capsys):
        cache = {f"id{i}": [] for i in range(4)}
        cache["id5"] = ["phrase"]
        du.validate_extraction_cache(cache, "benefit")
        captured = capsys.readouterr()
        assert "WARN" in captured.out
        assert "benefit" in captured.out

    def test_custom_threshold(self):
        cache = {"id1": [], "id2": ["phrase"], "id3": ["phrase"]}
        assert du.validate_extraction_cache(cache, "concern", warn_threshold=0.20) is False
        assert du.validate_extraction_cache(cache, "concern", warn_threshold=0.50) is True


# ===========================================================================
# CIP-0006 / Bug: filter_missing_source_text
# ===========================================================================

class TestFilterMissingSourceText:
    def test_no_missing_returns_unchanged(self):
        df = pd.DataFrame({"text": ["hello world", "foo bar"], "val": [1, 2]})
        result = du.filter_missing_source_text(df)
        assert len(result) == 2

    def test_nan_rows_dropped(self, capsys):
        df = pd.DataFrame({"text": ["hello", None, "world"], "val": [1, 2, 3]})
        result = du.filter_missing_source_text(df)
        assert len(result) == 2
        assert "WARN" in capsys.readouterr().out

    def test_empty_string_rows_dropped(self, capsys):
        df = pd.DataFrame({"text": ["hello", "   ", "world"], "val": [1, 2, 3]})
        result = du.filter_missing_source_text(df)
        assert len(result) == 2
        assert "WARN" in capsys.readouterr().out

    def test_custom_column_name(self):
        df = pd.DataFrame({"chunk_text": ["hello", None], "val": [1, 2]})
        result = du.filter_missing_source_text(df, text_col="chunk_text")
        assert len(result) == 1

    def test_returns_copy_not_view(self):
        df = pd.DataFrame({"text": ["hello", "world"], "val": [1, 2]})
        result = du.filter_missing_source_text(df)
        result["val"] = 99
        assert df["val"].tolist() == [1, 2]


# ===========================================================================
# CIP-0006: chunking filter (word-boundary)
# ===========================================================================

class TestChunkingFilter:
    def test_short_paragraphs_excluded(self, tmp_path):
        """Paragraphs below min_chunk_words must NOT appear in the output."""
        fitz = pytest.importorskip("fitz", reason="PyMuPDF not installed")
        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "Short.\n\nThis is a much longer paragraph with enough words to pass the minimum word count filter for the extraction pipeline.")
        doc.save(str(pdf_path))
        doc.close()

        chunks = du.extract_chunks_from_pdf(str(pdf_path), {}, min_chunk_words=10)
        texts = [c["text"] for c in chunks]
        assert not any(t.strip() == "Short." for t in texts), "Short paragraph should be filtered"
        assert any("longer paragraph" in t for t in texts), "Long paragraph should be kept"

    def test_all_chunks_meet_min_words(self, tmp_path):
        """Every chunk in the output must satisfy the word count filter."""
        fitz = pytest.importorskip("fitz", reason="PyMuPDF not installed")
        pdf_path = tmp_path / "test2.pdf"
        doc = fitz.open()
        page = doc.new_page()
        lines = "\n\n".join([
            "x",
            "This paragraph has more than ten words so it should pass the filter check.",
            "y z",
            "Another longer paragraph that definitely meets the minimum word count requirement here.",
        ])
        page.insert_text((50, 72), lines)
        doc.save(str(pdf_path))
        doc.close()

        chunks = du.extract_chunks_from_pdf(str(pdf_path), {}, min_chunk_words=10)
        for chunk in chunks:
            assert chunk["word_count"] >= 10, f"Chunk below min_words: {chunk['text']!r}"


# ===========================================================================
# Bug: tech-word filter uses word-boundary matching (Issue 6b)
# ===========================================================================

class TestTechWordBoundaryMatching:
    def _extract(self, phrase_text, tech_words):
        client = _mock_client(phrase_text)
        return du.extract_phrases(_make_row(), kind="concern", client=client, tech_words=tech_words)

    def test_gm_does_not_match_stigma(self):
        result = self._extract("stigma around the technology", tech_words=["gm"])
        assert "stigma around the technology" in result.retained_phrases

    def test_gm_does_not_match_algorithm(self):
        result = self._extract("concerns about the algorithm", tech_words=["gm"])
        assert "concerns about the algorithm" in result.retained_phrases

    def test_gm_matches_gm_crops(self):
        result = self._extract("concerns about gm crops", tech_words=["gm"])
        assert "concerns about gm crops" not in result.retained_phrases
        assert any("gm" in drop[1] for drop in result.dropped_by_filter)

    def test_ai_matches_whole_word(self):
        result = self._extract("fear of ai systems", tech_words=["ai"])
        assert "fear of ai systems" not in result.retained_phrases

    def test_ai_does_not_match_inside_word(self):
        result = self._extract("maintaining public trust", tech_words=["ai"])
        assert "maintaining public trust" in result.retained_phrases


# ===========================================================================
# CIP-0007: label_cluster does not leak technology metadata
# ===========================================================================

class TestLabelClusterNoTechLeak:
    def _exemplars(self):
        return [
            {"concern": "job loss risk", "technology": "AI"},
            {"concern": "workplace disruption", "technology": "Nuclear"},
        ]

    def test_prompt_does_not_contain_technology_name(self):
        """The LLM prompt must not include '(from AI)' or '(from Nuclear)'."""
        client = MagicMock(spec=LLMClient)
        client.complete.return_value = (
            '{"label": "Employment", "description": "Jobs.", "key_terms": ["jobs"]}'
        )
        du.label_cluster(1, self._exemplars(), True, kind="concern", client=client)
        call_args = client.complete.call_args
        messages = call_args[0][0]  # first positional arg is the messages list
        full_prompt = " ".join(
            m["content"] for m in messages if isinstance(m.get("content"), str)
        )
        assert "(from AI)" not in full_prompt
        assert "(from Nuclear)" not in full_prompt
        assert "from AI" not in full_prompt

    def test_phrase_text_still_included(self):
        """The exemplar phrases themselves must still appear in the prompt."""
        client = MagicMock(spec=LLMClient)
        client.complete.return_value = (
            '{"label": "Employment", "description": "Jobs.", "key_terms": ["jobs"]}'
        )
        du.label_cluster(1, self._exemplars(), True, kind="concern", client=client)
        call_args = client.complete.call_args
        messages = call_args[0][0]
        full_prompt = " ".join(
            m["content"] for m in messages if isinstance(m.get("content"), str)
        )
        assert "job loss risk" in full_prompt
        assert "workplace disruption" in full_prompt


# ===========================================================================
# CROSSCUTTING_ENTROPY_THRESHOLD constant
# ===========================================================================

class TestCrosscuttingThreshold:
    def test_constant_exists(self):
        assert hasattr(du, "CROSSCUTTING_ENTROPY_THRESHOLD")

    def test_constant_is_float_in_range(self):
        t = du.CROSSCUTTING_ENTROPY_THRESHOLD
        assert isinstance(t, float)
        assert 0.0 < t < 1.0

    def test_constant_value_is_half(self):
        assert du.CROSSCUTTING_ENTROPY_THRESHOLD == 0.5


# ===========================================================================
# v19 Chunker helpers: _split_into_sentences and _repack_sentences_into_chunks
# ===========================================================================

class TestSplitIntoSentences:
    def test_basic_split(self):
        text = "The sky is blue. The grass is green. Stars are bright."
        result = du._split_into_sentences(text)
        assert len(result) == 3

    def test_collapses_whitespace(self):
        text = "First  sentence.\nSecond sentence."
        result = du._split_into_sentences(text)
        assert all("\n" not in s for s in result)

    def test_empty_string(self):
        assert du._split_into_sentences("") == []

    def test_no_sentence_boundary(self):
        text = "This is a single sentence with no terminator"
        result = du._split_into_sentences(text)
        assert len(result) == 1
        assert result[0] == text


class TestRepackSentencesIntoChunks:
    def test_single_sentence_fits(self):
        sentences = ["Short sentence."]
        result = du._repack_sentences_into_chunks(sentences, target_words=300)
        assert result == ["Short sentence."]

    def test_multiple_sentences_packed_together(self):
        sentences = ["Sentence one." for _ in range(5)]
        result = du._repack_sentences_into_chunks(sentences, target_words=300)
        # all five sentences fit well under 300 words, so should be one chunk
        assert len(result) == 1
        assert "Sentence one." in result[0]

    def test_oversized_sentence_is_its_own_chunk(self):
        big = " ".join(["word"] * 350)
        sentences = ["Short intro.", big, "Short outro."]
        result = du._repack_sentences_into_chunks(sentences, target_words=300)
        # The oversized sentence should be its own chunk
        assert any(len(c.split()) >= 300 for c in result)

    def test_empty_input(self):
        assert du._repack_sentences_into_chunks([], target_words=300) == []


class TestParagraphSplit:
    def test_double_newline_splits(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = du._paragraph_split(text)
        assert len(result) == 3

    def test_collapses_internal_whitespace(self):
        text = "First  para.\n\nSecond para."
        result = du._paragraph_split(text)
        assert all("  " not in p for p in result)

    def test_empty_paragraphs_excluded(self):
        text = "Para one.\n\n\n\nPara two."
        result = du._paragraph_split(text)
        assert len(result) == 2

    def test_empty_string(self):
        assert du._paragraph_split("") == []


# ===========================================================================
# v19 Three-case chunker: extract_chunks_from_pdf
# ===========================================================================

def _make_fitz_mock(text: str):
    """Return a fake fitz module whose open() yields *text* from one page.

    The page's ``get_text`` handles both plain-text (``get_text()``) and
    blocks (``get_text("blocks")``) modes.  For blocks mode, each
    double-newline-separated paragraph is returned as a single text block
    tuple ``(0, i, 100, i+1, para_text, i, 0)``, so the blocks path
    produces the same paragraphs as the text-newline path.
    """
    def _get_text(mode=None):
        if mode == "blocks":
            paras = [p.strip() for p in text.split("\n\n") if p.strip()]
            return [(0, i, 100, i + 1, p, i, 0) for i, p in enumerate(paras)]
        return text

    page = MagicMock()
    page.get_text.side_effect = _get_text
    doc = MagicMock()
    # Use side_effect so each iteration gets a fresh iterator (the doc is
    # iterated twice: once for blocks, once for plain text).
    doc.__iter__ = MagicMock(side_effect=lambda: iter([page]))
    doc.close = MagicMock()
    fake_fitz = MagicMock()
    fake_fitz.open.return_value = doc
    return fake_fitz


class TestExtractChunksFromPdfV19:
    """Tests for the v19 three-case hybrid chunker.

    These tests inject a fake ``fitz`` module via ``sys.modules`` so no real
    PDFs or PyMuPDF installation are required.  The mock returns blocks that
    match the double-newline paragraph structure, so the blocks-primary path
    is exercised for tests that have proper paragraph breaks, and the
    sentence-fallback path is exercised for tests with no paragraph breaks.
    """

    def _make_pdf_text(self, n_paragraphs: int, words_each: int = 60) -> str:
        """Build a fake PDF text with *n_paragraphs* double-newline-separated paras."""
        para = " ".join(["word"] * words_each)
        return "\n\n".join([para] * n_paragraphs)

    def _call_extractor(self, full_text: str, **kwargs):
        """Call extract_chunks_from_pdf with a mocked fitz and return chunks."""
        import sys
        du.reset_chunk_stats()
        fake_fitz = _make_fitz_mock(full_text)
        with patch.dict(sys.modules, {"fitz": fake_fitz}):
            return du.extract_chunks_from_pdf(
                Path("fake.pdf"),
                {"technology": "AI", "year": 2023},
                **kwargs
            )

    # ---- Case 1: paragraph-only ------------------------------------------

    def test_case1_all_chunks_are_paragraph_method(self):
        """Clean paragraphs → all chunks labelled 'paragraph'."""
        text = self._make_pdf_text(n_paragraphs=5, words_each=60)
        chunks = self._call_extractor(text)
        assert len(chunks) >= 3
        assert all(c["chunking_method"] == "paragraph" for c in chunks)

    def test_case1_stats_document_paragraph_only(self):
        text = self._make_pdf_text(n_paragraphs=5, words_each=60)
        self._call_extractor(text)
        stats = du.get_chunk_stats()
        assert stats["documents_paragraph_only"] == 1
        assert stats["documents_sentence_fallback"] == 0
        assert stats["documents_paragraph_with_split"] == 0

    def test_case1_chunks_contain_was_truncated_field(self):
        text = self._make_pdf_text(n_paragraphs=5, words_each=60)
        chunks = self._call_extractor(text)
        assert all("was_truncated" in c for c in chunks)
        assert all(c["was_truncated"] is False for c in chunks)

    # ---- Case 2: paragraph + internal sentence-split ---------------------

    def test_case2_oversized_paragraph_is_split(self):
        """One oversized paragraph → some chunks have 'sentence_split' method."""
        normal = " ".join(["word"] * 60)
        # Build a paragraph that exceeds MAX_CHUNK_WORDS (500) by using a text
        # with clear sentence boundaries so the splitter can divide it.
        big_para = (
            "This is sentence one. " * 30
        )  # ~120 words — use max_chunk_words=100 in call
        text = f"{normal}\n\n{normal}\n\n{normal}\n\n{big_para}"
        chunks = self._call_extractor(text, max_chunk_words=100,
                                      sentence_fallback_target_words=50)
        methods = {c["chunking_method"] for c in chunks}
        assert "sentence_split" in methods
        assert "paragraph" in methods

    def test_case2_stats_paragraph_with_split(self):
        normal = " ".join(["word"] * 60)
        big_para = "This is sentence one. " * 30
        text = f"{normal}\n\n{normal}\n\n{normal}\n\n{big_para}"
        self._call_extractor(text, max_chunk_words=100,
                             sentence_fallback_target_words=50)
        stats = du.get_chunk_stats()
        assert stats["documents_paragraph_with_split"] == 1
        assert stats["documents_sentence_fallback"] == 0

    # ---- Case 3: full sentence fallback ----------------------------------

    def test_case3_no_paragraph_breaks_triggers_fallback(self):
        """Text with no double-newlines → all chunks are 'sentence_fallback'."""
        # Single block of text, no double newlines
        text = ("This is sentence one. This is sentence two. " * 20)
        chunks = self._call_extractor(text,
                                      min_chunk_words=5,
                                      min_chunk_chars=10,
                                      sentence_fallback_min_paragraphs=3)
        assert len(chunks) > 0
        assert all(c["chunking_method"] == "sentence_fallback" for c in chunks)

    def test_case3_stats_sentence_fallback(self):
        text = "This is sentence one. This is sentence two. " * 20
        self._call_extractor(text, min_chunk_words=5, min_chunk_chars=10,
                             sentence_fallback_min_paragraphs=3)
        stats = du.get_chunk_stats()
        assert stats["documents_sentence_fallback"] == 1
        assert stats["documents_paragraph_only"] == 0
        assert stats["documents_paragraph_with_split"] == 0

    # ---- General output schema -------------------------------------------

    def test_chunks_contain_required_fields(self):
        text = self._make_pdf_text(n_paragraphs=4, words_each=60)
        chunks = self._call_extractor(text)
        required = {"text", "source_file", "chunk_index", "word_count",
                    "was_truncated", "chunking_method", "technology",
                    "technology_meta", "year"}
        for c in chunks:
            assert required.issubset(c.keys()), f"Missing keys: {required - c.keys()}"

    def test_chunks_below_word_floor_excluded(self):
        """Chunks below min_chunk_words must not appear in the output."""
        # Use paragraphs of 10 words with a floor of 20
        text = self._make_pdf_text(n_paragraphs=5, words_each=10)
        chunks = self._call_extractor(text, min_chunk_words=20)
        assert all(c["word_count"] >= 20 for c in chunks)

    def test_reset_chunk_stats_clears_accumulator(self):
        text = self._make_pdf_text(n_paragraphs=4, words_each=60)
        self._call_extractor(text)
        du.reset_chunk_stats()
        stats = du.get_chunk_stats()
        assert all(v == 0 for v in stats.values())


# ===========================================================================
# Chunking constants (v19 defaults)
# ===========================================================================

class TestRunSensitivityEntropyConsistency:
    """Verify run_sensitivity uses normalized_entropy (values in [0,1])."""

    def _minimal_df(self, n: int = 30):
        """Build a minimal concerns DataFrame with cluster_id and technology columns."""
        techs = ["AI"] * (n // 2) + ["Nuclear"] * (n // 2)
        return pd.DataFrame({
            "concern": [f"phrase {i}" for i in range(n)],
            "technology_meta": techs,
            "cluster_id": list(range(n // 2)) * 2,
            "year": [2022] * n,
        })

    def test_stable_core_entropy_values_in_unit_interval(self, tmp_path):
        """Entropy column in the stable-core CSV must be in [0, 1]."""
        df = self._minimal_df()
        n_phrases = len(df)
        embeddings = np.random.default_rng(0).random((n_phrases, 8))
        # Normalise rows to unit length (as the pipeline does)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / np.where(norms == 0, 1, norms)

        du.run_sensitivity(
            k=3,
            kind="concern",
            embeddings_normalized=embeddings,
            df=df,
            output_folder=tmp_path,
        )

        csv_path = tmp_path / "concern_sensitivity_stable_core_k3.csv"
        assert csv_path.exists(), "stable-core CSV not written"
        stable = pd.read_csv(csv_path)
        assert "tech_entropy" in stable.columns
        assert (stable["tech_entropy"] >= 0).all(), "entropy below 0"
        assert (stable["tech_entropy"] <= 1).all(), "entropy above 1"

    def test_uniform_technology_cluster_entropy_above_threshold(self, tmp_path):
        """A cluster spread equally across technologies should score > 0.5."""
        n = 40
        # 4 technologies, 10 phrases each, all in the same cluster
        techs = ["AI"] * 10 + ["Nuclear"] * 10 + ["Genetic"] * 10 + ["Nano"] * 10
        df = pd.DataFrame({
            "concern": [f"phrase {i}" for i in range(n)],
            "technology_meta": techs,
            "cluster_id": [0] * n,
            "year": [2022] * n,
        })
        embeddings = np.random.default_rng(1).random((n, 8))
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / np.where(norms == 0, 1, norms)

        du.run_sensitivity(
            k=2,
            kind="concern",
            embeddings_normalized=embeddings,
            df=df,
            output_folder=tmp_path,
        )

        stable = pd.read_csv(tmp_path / "concern_sensitivity_stable_core_k2.csv")
        # The cluster with all 4 technologies equally should have high entropy
        max_entropy = stable["tech_entropy"].max()
        assert max_entropy > 0.5, (
            f"Expected at least one cluster with entropy > 0.5; got max={max_entropy}"
        )


class TestExtractParagraphsFromBlocks:
    """Tests for _extract_paragraphs_from_blocks — the layout-aware extractor."""

    def _make_doc_with_blocks(self, block_texts: list):
        """Build a mock fitz doc where get_text('blocks') returns block_texts."""
        blocks = []
        for i, text in enumerate(block_texts):
            # (x0, y0, x1, y1, text, block_no, block_type=0)
            blocks.append((0, i * 20, 100, (i + 1) * 20, text, i, 0))

        page = MagicMock()
        page.get_text.return_value = blocks  # called with "blocks"

        doc = MagicMock()
        doc.__iter__ = MagicMock(return_value=iter([page]))
        return doc

    def test_returns_text_from_each_block(self):
        doc = self._make_doc_with_blocks(["First para.", "Second para.", "Third para."])
        result = du._extract_paragraphs_from_blocks(doc)
        assert result == ["First para.", "Second para.", "Third para."]

    def test_skips_image_blocks(self):
        page = MagicMock()
        page.get_text.return_value = [
            (0, 0, 100, 20, "Text block.", 0, 0),   # block_type=0 → include
            (0, 20, 100, 40, "[image]", 1, 1),       # block_type=1 → skip
            (0, 40, 100, 60, "More text.", 2, 0),    # block_type=0 → include
        ]
        doc = MagicMock()
        doc.__iter__ = MagicMock(return_value=iter([page]))
        result = du._extract_paragraphs_from_blocks(doc)
        assert result == ["Text block.", "More text."]

    def test_empty_blocks_return_empty_list(self):
        page = MagicMock()
        page.get_text.return_value = []
        doc = MagicMock()
        doc.__iter__ = MagicMock(return_value=iter([page]))
        assert du._extract_paragraphs_from_blocks(doc) == []

    def test_whitespace_normalised(self):
        doc = self._make_doc_with_blocks(["Line one\nLine two  continued."])
        result = du._extract_paragraphs_from_blocks(doc)
        assert result == ["Line one Line two continued."]


class TestExtractChunksPdfBlocksPrimary:
    """Tests that extract_chunks_from_pdf uses blocks as the primary paragraph source."""

    def _blocks_from_texts(self, texts: list) -> list:
        """Turn a list of strings into fitz-style block tuples."""
        return [
            (0, i * 20, 100, (i + 1) * 20, t, i, 0)
            for i, t in enumerate(texts)
        ]

    def _make_fitz_with_blocks(self, block_texts: list, plain_text: str = ""):
        """Return a fake fitz module whose open() yields blocks + plain text."""
        blocks = self._blocks_from_texts(block_texts)
        page = MagicMock()
        # get_text("blocks") → list of block tuples
        # get_text()         → plain string
        def get_text(mode=None):
            if mode == "blocks":
                return blocks
            return plain_text or " ".join(block_texts)
        page.get_text.side_effect = get_text

        doc = MagicMock()
        doc.__iter__ = MagicMock(side_effect=lambda: iter([page]))
        doc.close = MagicMock()

        fake_fitz = MagicMock()
        fake_fitz.open.return_value = doc
        return fake_fitz

    def _call(self, block_texts, plain_text="", **kwargs):
        import sys
        du.reset_chunk_stats()
        fake_fitz = self._make_fitz_with_blocks(block_texts, plain_text)
        with patch.dict(sys.modules, {"fitz": fake_fitz}):
            return du.extract_chunks_from_pdf(
                Path("fake.pdf"),
                {"technology": "AI", "year": 2023},
                **kwargs
            )

    def test_blocks_primary_used_when_enough_blocks(self):
        """When blocks give ≥3 substantive paragraphs, blocks_primary stat increments."""
        paras = [" ".join(["word"] * 60)] * 5
        self._call(paras)
        assert du.get_chunk_stats()["documents_blocks_primary"] == 1
        assert du.get_chunk_stats()["documents_text_newline_primary"] == 0

    def test_text_newline_fallback_when_blocks_too_few(self):
        """When blocks give <3 substantive paragraphs, text-newline fallback is used."""
        # Only 1 block (short), but plain_text has clean double-newlines
        short_block = ["hi"]  # below word floor
        good_plain = "\n\n".join([" ".join(["word"] * 60)] * 5)
        self._call(short_block, plain_text=good_plain,
                   min_chunk_words=40, min_chunk_chars=80)
        assert du.get_chunk_stats()["documents_text_newline_primary"] == 1
        assert du.get_chunk_stats()["documents_blocks_primary"] == 0

    def test_blocks_primary_produces_paragraph_method(self):
        """Chunks from block paragraphs are labelled 'paragraph'."""
        paras = [" ".join(["word"] * 60)] * 5
        chunks = self._call(paras)
        assert all(c["chunking_method"] == "paragraph" for c in chunks)

    def test_pdf_without_double_newlines_recovered_by_blocks(self):
        """A PDF with no \\n\\n in text but good blocks → uses blocks, not sentence_fallback."""
        # Simulate a PDF where plain text extraction produces no double-newlines
        # (would have triggered case-3 in the old chunker) but blocks are good.
        paras = [" ".join(["word"] * 60)] * 5
        plain_no_breaks = " ".join(paras)  # no \n\n at all
        chunks = self._call(paras, plain_text=plain_no_breaks)
        # Should NOT be sentence_fallback because blocks gave enough paragraphs
        assert all(c["chunking_method"] != "sentence_fallback" for c in chunks)
        assert du.get_chunk_stats()["documents_blocks_primary"] == 1
        assert du.get_chunk_stats()["documents_sentence_fallback"] == 0

    def test_stats_include_new_keys(self):
        """The chunk stats dict must contain the new paragraph-source keys."""
        stats = du.get_chunk_stats()
        assert "documents_blocks_primary" in stats
        assert "documents_text_newline_primary" in stats


class TestChunkingConstants:
    def test_min_chunk_words_is_40(self):
        assert du.MIN_CHUNK_WORDS == 40

    def test_min_chunk_chars_is_80(self):
        assert du.MIN_CHUNK_CHARS == 80

    def test_max_chunk_words_is_500(self):
        assert du.MAX_CHUNK_WORDS == 500

    def test_sentence_fallback_target_is_300(self):
        assert du.SENTENCE_FALLBACK_TARGET_WORDS == 300

    def test_sentence_fallback_min_paragraphs_is_3(self):
        assert du.SENTENCE_FALLBACK_MIN_PARAGRAPHS == 3


# ===========================================================================
# load_artifacts()
# ===========================================================================

class TestLoadArtifacts:
    """Verify load_artifacts() returns all expected keys with correct types."""

    @pytest.fixture()
    def artifact_dirs(self, tmp_path):
        """Create synthetic artifact files that mirror what 01_processing writes."""
        out  = tmp_path / "outputs"
        ckpt = tmp_path / "checkpoints"
        out.mkdir()
        ckpt.mkdir()

        # --- DataFrames ---
        pd.DataFrame({"chunk_id": ["c0"], "text": ["hello"], "word_count": [1]}).to_csv(
            out / "paragraph_chunks.csv", index=False)
        pd.DataFrame({"concern": ["test"], "chunk_id": ["c0"]}).to_csv(
            out / "extracted_concerns.csv", index=False)
        pd.DataFrame({"benefit": ["test"], "chunk_id": ["c0"]}).to_csv(
            out / "extracted_benefits.csv", index=False)
        pd.DataFrame({"cluster_id": [0], "label": ["Cluster 0"], "size": [1]}).to_csv(
            out / "cluster_summary.csv", index=False)
        pd.DataFrame({"cluster_id": [0], "label": ["Benefit Cluster 0"], "size": [1]}).to_csv(
            out / "benefit_cluster_summary.csv", index=False)

        # --- Numpy arrays ---
        np.save(ckpt / "concern_embeddings.npy",       np.zeros((1, 4)))
        np.save(ckpt / "benefit_embeddings.npy",       np.zeros((1, 4)))
        np.save(ckpt / "cluster_centroids.npy",        np.zeros((2, 4)))
        np.save(ckpt / "benefit_cluster_centroids.npy", np.zeros((2, 4)))

        # --- JSON files ---
        (ckpt / "concern_ids.json").write_text(json.dumps(["id0"]))
        (ckpt / "benefit_ids.json").write_text(json.dumps(["id0"]))
        (out  / "cluster_labels.json").write_text(json.dumps({"0": "Label A"}))
        (out  / "benefit_cluster_labels.json").write_text(json.dumps({"0": "Benefit A"}))
        (out  / "framing_lens_mappings.json").write_text(
            json.dumps({"Lens1": {"cluster_ids": [0]}}))
        (out  / "benefit_framing_lens_mappings.json").write_text(
            json.dumps({"BenLens1": {"cluster_ids": [0]}}))

        # --- Entropy JSON files (written by add-entropy-saves task) ---
        (out / "cluster_entropy.json").write_text(json.dumps({
            "raw":  {"0": 0.8, "1": 0.2},
            "norm": {"0": 0.6, "1": 0.1},
            "cross_cutting": [0],
        }))
        (out / "benefit_cluster_entropy.json").write_text(json.dumps({
            "raw":  {"0": 0.7},
            "norm": {"0": 0.5},
            "cross_cutting": [0],
        }))

        return out, ckpt

    def test_all_keys_present(self, artifact_dirs):
        out, ckpt = artifact_dirs
        a = du.load_artifacts(out, ckpt)
        expected_keys = {
            "chunks_df", "concerns_df", "benefits_df",
            "cluster_summary_df", "benefit_cluster_summary_df",
            "concern_embeddings", "benefit_embeddings",
            "concern_centroids", "benefit_centroids",
            "concern_ids", "benefit_ids",
            "cluster_labels", "benefit_cluster_labels",
            "framing_lens_mappings", "benefit_framing_lens_mappings",
            "cluster_entropy", "cluster_entropy_norm", "cross_cutting_clusters",
            "benefit_cluster_entropy", "normalized_entropy_benefits",
            "cross_cutting_clusters_benefits",
        }
        assert expected_keys == set(a.keys())

    def test_dataframes_are_dataframes(self, artifact_dirs):
        out, ckpt = artifact_dirs
        a = du.load_artifacts(out, ckpt)
        for key in ("chunks_df", "concerns_df", "benefits_df",
                    "cluster_summary_df", "benefit_cluster_summary_df"):
            assert isinstance(a[key], pd.DataFrame), f"{key} should be a DataFrame"

    def test_numpy_arrays_correct_shape(self, artifact_dirs):
        out, ckpt = artifact_dirs
        a = du.load_artifacts(out, ckpt)
        assert isinstance(a["concern_embeddings"], np.ndarray)
        assert a["concern_embeddings"].shape == (1, 4)
        assert a["concern_centroids"].shape == (2, 4)

    def test_entropy_dicts_have_int_keys(self, artifact_dirs):
        out, ckpt = artifact_dirs
        a = du.load_artifacts(out, ckpt)
        for key in ("cluster_entropy", "cluster_entropy_norm",
                    "benefit_cluster_entropy", "normalized_entropy_benefits"):
            assert all(isinstance(k, int) for k in a[key]), \
                f"{key} keys should be int"

    def test_cross_cutting_clusters_is_list(self, artifact_dirs):
        out, ckpt = artifact_dirs
        a = du.load_artifacts(out, ckpt)
        assert isinstance(a["cross_cutting_clusters"], list)
        assert isinstance(a["cross_cutting_clusters_benefits"], list)
        assert a["cross_cutting_clusters"] == [0]

    def test_entropy_values_correct(self, artifact_dirs):
        out, ckpt = artifact_dirs
        a = du.load_artifacts(out, ckpt)
        assert a["cluster_entropy"][0] == pytest.approx(0.8)
        assert a["cluster_entropy_norm"][1] == pytest.approx(0.1)

    def test_missing_file_raises(self, tmp_path):
        out  = tmp_path / "out"
        ckpt = tmp_path / "ckpt"
        out.mkdir(); ckpt.mkdir()
        with pytest.raises((FileNotFoundError, OSError)):
            du.load_artifacts(out, ckpt)


# ===========================================================================
# LLMClient wrapper — mocked litellm
# ===========================================================================

class TestLLMClient:
    """Tests for pub_dialogue.client.LLMClient.

    litellm is patched at the module level inside each method (lazy import),
    so we patch it on the client module, not at the top-level import.
    """

    def _make_litellm_completion(self, content: str):
        resp = MagicMock()
        resp.choices[0].message.content = content
        return resp

    def _make_litellm_embedding(self, vectors: list):
        resp = MagicMock()
        resp.data = [MagicMock(embedding=v) for v in vectors]
        return resp

    def test_complete_returns_string(self):
        client = LLMClient(model="gpt-4o-mini")
        with patch("litellm.completion") as mock_comp:
            mock_comp.return_value = self._make_litellm_completion("hello world")
            result = client.complete([{"role": "user", "content": "Hi"}])
        assert result == "hello world"

    def test_complete_passes_model_and_messages(self):
        client = LLMClient(model="claude-3-5-haiku-latest")
        with patch("litellm.completion") as mock_comp:
            mock_comp.return_value = self._make_litellm_completion("ok")
            client.complete([{"role": "user", "content": "test"}], max_tokens=100)
        mock_comp.assert_called_once_with(
            model="claude-3-5-haiku-latest",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=100,
        )

    def test_embed_returns_list_of_vectors(self):
        client = LLMClient(embedding_model="text-embedding-3-large")
        vecs = [[0.1, 0.2], [0.3, 0.4]]
        with patch("litellm.embedding") as mock_emb:
            mock_emb.return_value = self._make_litellm_embedding(vecs)
            result = client.embed(["hello", "world"])
        assert result == vecs

    def test_embed_passes_embedding_model(self):
        client = LLMClient(embedding_model="text-embedding-3-large")
        with patch("litellm.embedding") as mock_emb:
            mock_emb.return_value = self._make_litellm_embedding([[0.0]])
            client.embed(["text"])
        mock_emb.assert_called_once_with(
            model="text-embedding-3-large", input=["text"]
        )

    @pytest.mark.parametrize("model", [
        "gpt-4o-mini",
        "claude-3-5-haiku-latest",
        "gemini/gemini-2.0-flash",
    ])
    def test_provider_routing_no_import_error(self, model):
        """Constructing LLMClient with any provider string must not raise."""
        client = LLMClient(model=model)
        assert client.model == model

    def test_default_model(self):
        client = LLMClient()
        assert client.model == "gpt-4o-mini"
        assert client.embedding_model == "text-embedding-3-large"
