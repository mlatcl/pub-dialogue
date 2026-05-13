"""
tests/test_assess.py — tests for pub_dialogue.assess module.

Covers heuristic flags, plot_data_quality, flag_chunk_quality,
vocabulary_frequency_diagnostic, and assess-only utilities.

entropy_by_year and validate_extraction_cache are now in pub_dialogue.address
(address-stage outputs) and are tested via test_address.py.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

import pub_dialogue.assess as assess
import pub_dialogue.address as address


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunks_df(n=20, seed=0):
    rng = np.random.default_rng(seed)
    techs = ["AI", "Nuclear", "GM"]
    years = list(range(2015, 2025))
    return pd.DataFrame({
        "chunk_id": [f"c{i}" for i in range(n)],
        "technology_meta": rng.choice(techs, size=n),
        "year": rng.choice(years, size=n),
        "source_file": [f"doc_{i % 5}.pdf" for i in range(n)],
        "word_count": rng.integers(40, 300, size=n),
        "text": [f"Sample text number {i}." for i in range(n)],
    })


# ===========================================================================
# Content-quality heuristics
# ===========================================================================

# ===========================================================================
# AssessStage dataclass (CIP-0010 Phase 1)
# ===========================================================================

class TestAssessStageDefaults:
    """Verify AssessStage can be instantiated and holds an AccessStage reference."""

    def test_instantiation(self):
        from pub_dialogue.access import AccessStage
        from pub_dialogue.assess import AssessStage
        a = AccessStage()
        stage = AssessStage(access=a)
        assert stage.access is a

    def test_access_folder_accessible_via_stage(self):
        from pathlib import Path
        from pub_dialogue.access import AccessStage
        from pub_dialogue.assess import AssessStage
        a = AccessStage(output_folder=Path("custom"))
        stage = AssessStage(access=a)
        assert stage.access.output_folder == Path("custom")


class TestLooksLikeBibliography:
    def test_doi_plus_year_flagged(self):
        text = "Smith et al. doi:10.1000/xyz (2020)"
        assert assess._looks_like_bibliography(text)

    def test_plain_text_not_flagged(self):
        text = "People were worried about the impact of technology on jobs."
        assert not assess._looks_like_bibliography(text)

    def test_non_string_returns_false(self):
        assert not assess._looks_like_bibliography(None)
        assert not assess._looks_like_bibliography(42)

    def test_doi_without_year_not_flagged(self):
        text = "See doi:10.1000/xyz for details."
        assert not assess._looks_like_bibliography(text)


class TestLooksLikeTableRow:
    def test_two_percent_signs_flagged(self):
        assert assess._looks_like_table_row("Agrees 45% Disagrees 30%")

    def test_single_percent_not_flagged(self):
        assert not assess._looks_like_table_row("About 50% of respondents agreed.")

    def test_non_string_returns_false(self):
        assert not assess._looks_like_table_row(None)


# ===========================================================================
# flag_chunk_quality
# ===========================================================================

class TestFlagChunkQuality:
    def test_adds_flag_columns(self, tmp_path):
        df = _make_chunks_df()
        result = assess.flag_chunk_quality(df, tmp_path)
        assert "likely_bibliography" in result.columns
        assert "likely_table_row" in result.columns

    def test_returns_dataframe_same_length(self, tmp_path):
        df = _make_chunks_df(30)
        result = assess.flag_chunk_quality(df, tmp_path)
        assert len(result) == 30

    def test_writes_flagged_csv(self, tmp_path):
        df = _make_chunks_df()
        assess.flag_chunk_quality(df, tmp_path)
        assert (tmp_path / "chunk_quality_flagged.csv").exists()

    def test_does_not_drop_rows(self, tmp_path):
        df = _make_chunks_df(10)
        result = assess.flag_chunk_quality(df, tmp_path)
        assert len(result) == len(df)

    def test_bibliography_text_gets_flagged(self, tmp_path):
        df = pd.DataFrame({
            "chunk_id": ["c0"],
            "source_file": ["f.pdf"],
            "word_count": [50],
            "text": ["Smith et al. doi:10.1000/xyz (2020)"],
        })
        result = assess.flag_chunk_quality(df, tmp_path)
        assert result["likely_bibliography"].iloc[0]


# ===========================================================================
# plot_data_quality
# ===========================================================================

class TestPlotDataQuality:
    def test_saves_png_and_returns_path(self, tmp_path):
        pytest.importorskip("matplotlib")
        df = _make_chunks_df()
        path = assess.plot_data_quality(df, tmp_path)
        assert path.exists()
        assert path.suffix == ".png"

    def test_custom_filename(self, tmp_path):
        pytest.importorskip("matplotlib")
        df = _make_chunks_df()
        path = assess.plot_data_quality(df, tmp_path, filename="test_output.png")
        assert path.name == "test_output.png"

    def test_creates_output_dir_if_absent(self, tmp_path):
        pytest.importorskip("matplotlib")
        new_dir = tmp_path / "subdir"
        df = _make_chunks_df()
        assess.plot_data_quality(df, new_dir)
        assert new_dir.exists()


# ===========================================================================
# entropy_by_year
# ===========================================================================

class TestEntropyByYear:
    def _make_group(self, cluster_ids):
        return pd.DataFrame({"cluster_id": cluster_ids})

    def test_uniform_distribution_high_entropy(self):
        g = self._make_group([0, 1, 2, 3] * 5)
        e = address.entropy_by_year(g)
        assert e > 0.5

    def test_concentrated_distribution_zero_entropy(self):
        g = self._make_group([0] * 20)
        e = address.entropy_by_year(g)
        assert e == 0.0

    def test_empty_group_returns_zero(self):
        g = self._make_group([])
        e = address.entropy_by_year(g)
        assert e == 0.0

    def test_returns_float(self):
        g = self._make_group([0, 1, 2])
        assert isinstance(address.entropy_by_year(g), float)


# ===========================================================================
# filter_missing_source_text
# ===========================================================================

class TestFilterMissingSourceText:
    def test_drops_nan_rows(self):
        df = pd.DataFrame({"text": ["hello", None, "world"], "x": [1, 2, 3]})
        result = assess.filter_missing_source_text(df)
        assert len(result) == 2

    def test_keeps_non_empty_rows(self):
        df = pd.DataFrame({"text": ["a", "b", "c"]})
        result = assess.filter_missing_source_text(df)
        assert len(result) == 3

    def test_empty_string_dropped(self):
        df = pd.DataFrame({"text": ["hello", ""]})
        result = assess.filter_missing_source_text(df)
        assert len(result) == 1


# ===========================================================================
# is_privacy_text
# ===========================================================================

class TestIsPrivacyText:
    def test_personal_data_flagged(self):
        assert assess.is_privacy_text("My personal data was used without consent.")

    def test_generic_text_not_flagged(self):
        assert not assess.is_privacy_text("The committee discussed policy options.")


# ===========================================================================
# vocabulary_frequency_diagnostic
# ===========================================================================

class TestVocabularyFrequencyDiagnostic:
    def test_returns_dataframe(self, tmp_path):
        phrases = ["unfair automated decisions", "job displacement", "data privacy concerns"]
        result = assess.vocabulary_frequency_diagnostic(phrases, "concern", tmp_path)
        assert isinstance(result, pd.DataFrame)

    def test_writes_csv(self, tmp_path):
        phrases = ["privacy", "job loss", "transparency"]
        assess.vocabulary_frequency_diagnostic(phrases, "concern", tmp_path)
        csvs = list(tmp_path.glob("*.csv"))
        assert len(csvs) >= 1


# ===========================================================================
# validate_extraction_cache (moved to address; tested here via address module)
# ===========================================================================

class TestValidateExtractionCacheAssess:
    def test_valid_cache_with_few_empties(self):
        cache = {"c0": ["job loss"], "c1": ["privacy"], "c2": ["job loss"]}
        assert address.validate_extraction_cache(cache, "concern")

    def test_mostly_empty_cache_returns_false(self):
        cache = {f"c{i}": [] for i in range(10)}
        assert not address.validate_extraction_cache(cache, "concern", warn_threshold=0.0)
