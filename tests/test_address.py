"""
tests/test_address.py — tests for pub_dialogue.address module.

Covers ExtractionResult dataclass, assign_window, _parse_listcol,
_clean_for_xlsx, and constants.  Functions already tested via
test_dialogue_utils (extract_phrases, label_cluster, get_embeddings_batch,
run_sensitivity) are not duplicated here.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import pub_dialogue.address as address


# ===========================================================================
# Constants
# ===========================================================================

class TestAddressConstants:
    def test_crosscutting_threshold_in_range(self):
        assert 0.0 < address.CROSSCUTTING_ENTROPY_THRESHOLD <= 1.0

    def test_default_tech_words_non_empty(self):
        assert len(address.DEFAULT_TECH_WORDS) > 0

    def test_extraction_prompt_has_placeholder(self):
        assert "{text}" in address.EXTRACTION_PROMPT

    def test_benefit_prompt_has_placeholder(self):
        assert "{text}" in address.BENEFIT_EXTRACTION_PROMPT

    def test_sentinels_present(self):
        assert "NO_CONCERN" in address._SENTINELS
        assert "NO_BENEFIT" in address._SENTINELS


# ===========================================================================
# ExtractionResult dataclass
# ===========================================================================

class TestExtractionResult:
    def test_defaults(self):
        r = address.ExtractionResult(chunk_id="c0")
        assert r.raw_phrases == []
        assert r.retained_phrases == []
        assert r.dropped_by_filter == []
        assert r.sentinel_returned is False
        assert r.error is None

    def test_with_values(self):
        r = address.ExtractionResult(
            chunk_id="c1",
            raw_phrases=["a", "b"],
            retained_phrases=["a"],
            sentinel_returned=True,
        )
        assert r.chunk_id == "c1"
        assert r.retained_phrases == ["a"]
        assert r.sentinel_returned is True

    def test_error_field(self):
        r = address.ExtractionResult(chunk_id="c2", error="timeout")
        assert r.error == "timeout"


# ===========================================================================
# _complete_with_retry
# ===========================================================================

class TestCompleteWithRetry:
    """Tests for the retry helper that wraps client.complete()."""

    def _make_client(self, side_effects):
        """Return a mock client whose complete() raises/returns the given side_effects."""
        import unittest.mock as mock
        client = mock.MagicMock()
        client.complete.side_effect = side_effects
        return client

    def test_success_on_first_try(self):
        import unittest.mock as mock
        import litellm
        client = self._make_client(["hello"])
        result = address._complete_with_retry(client, [], max_tokens=10, max_retries=3)
        assert result == "hello"
        assert client.complete.call_count == 1

    def test_retries_on_rate_limit_then_succeeds(self):
        import unittest.mock as mock
        import litellm
        rate_exc = litellm.RateLimitError("rate limited", llm_provider="openai", model="gpt-4o-mini")
        client = self._make_client([rate_exc, rate_exc, "ok"])
        with mock.patch("time.sleep"):
            result = address._complete_with_retry(client, [], max_tokens=10, max_retries=5)
        assert result == "ok"
        assert client.complete.call_count == 3

    def test_raises_after_max_retries_exhausted(self):
        import unittest.mock as mock
        import litellm
        rate_exc = litellm.RateLimitError("rate limited", llm_provider="openai", model="gpt-4o-mini")
        client = self._make_client([rate_exc] * 4)
        with mock.patch("time.sleep"), pytest.raises(litellm.RateLimitError):
            address._complete_with_retry(client, [], max_tokens=10, max_retries=3)
        assert client.complete.call_count == 4  # 1 initial + 3 retries

    def test_non_rate_limit_error_propagates_immediately(self):
        import unittest.mock as mock
        client = self._make_client([ValueError("bad input"), "should not reach"])
        with mock.patch("time.sleep"), pytest.raises(ValueError):
            address._complete_with_retry(client, [], max_tokens=10, max_retries=3)
        assert client.complete.call_count == 1


class TestExtractPhrasesRetry:
    """Integration: extract_phrases surfaces retry behaviour via ExtractionResult."""

    def _make_row(self, chunk_id="c0", text="The public worries about this."):
        import pandas as pd
        row = pd.Series({"chunk_id": chunk_id, "text": text})
        return (0, row)

    def test_rate_limit_then_success_returns_result(self):
        import unittest.mock as mock
        import litellm
        rate_exc = litellm.RateLimitError("rate limited", llm_provider="openai", model="gpt-4o-mini")
        client = mock.MagicMock()
        client.complete.side_effect = [rate_exc, rate_exc, "Privacy concerns\nData misuse"]
        with mock.patch("time.sleep"):
            result = address.extract_phrases(self._make_row(), "concern", client, max_retries=5)
        assert result.error is None
        assert len(result.retained_phrases) > 0

    def test_all_retries_exhausted_returns_error_result(self):
        import unittest.mock as mock
        import litellm
        rate_exc = litellm.RateLimitError("rate limited", llm_provider="openai", model="gpt-4o-mini")
        client = mock.MagicMock()
        client.complete.side_effect = [rate_exc] * 4
        with mock.patch("time.sleep"):
            result = address.extract_phrases(self._make_row(), "concern", client, max_retries=3)
        assert result.error is not None
        assert "RateLimitError" in result.error


# ===========================================================================
# assign_window
# ===========================================================================

class TestAssignWindow:
    def test_early_year_first_window(self):
        assert address.assign_window(2010) == "2004-2017"

    def test_boundary_2017(self):
        assert address.assign_window(2017) == "2004-2017"

    def test_second_window(self):
        assert address.assign_window(2019) == "2018-2020"

    def test_boundary_2020(self):
        assert address.assign_window(2020) == "2018-2020"

    def test_third_window(self):
        assert address.assign_window(2022) == "2021-2023"

    def test_boundary_2023(self):
        assert address.assign_window(2023) == "2021-2023"

    def test_latest_window(self):
        assert address.assign_window(2024) == "2024-2025"

    def test_nan_returns_none(self):
        import math
        assert address.assign_window(float("nan")) is None

    def test_none_returns_none(self):
        import pandas as pd
        assert address.assign_window(pd.NA) is None


# ===========================================================================
# _parse_listcol
# ===========================================================================

class TestParseListcol:
    def test_json_list(self):
        result = address._parse_listcol('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_empty_string(self):
        assert address._parse_listcol("") == []

    def test_empty_brackets(self):
        assert address._parse_listcol("[]") == []

    def test_nan(self):
        import math
        assert address._parse_listcol(float("nan")) == []

    def test_fallback_csv_style(self):
        result = address._parse_listcol("['a', 'b']")
        assert len(result) == 2

    def test_returns_list(self):
        assert isinstance(address._parse_listcol("[1]"), list)


# ===========================================================================
# _clean_for_xlsx
# ===========================================================================

class TestCleanForXlsx:
    def test_removes_control_chars(self):
        dirty = "hello\x0Bworld"  # vertical tab
        assert address._clean_for_xlsx(dirty) == "helloworld"

    def test_keeps_normal_text(self):
        text = "Hello, world! 123"
        assert address._clean_for_xlsx(text) == text

    def test_keeps_newline_and_tab(self):
        text = "line1\nline2\ttabbed"
        assert address._clean_for_xlsx(text) == text

    def test_non_string_passthrough(self):
        assert address._clean_for_xlsx(42) == 42
        assert address._clean_for_xlsx(None) is None
        assert address._clean_for_xlsx(3.14) == 3.14

    def test_removes_null_byte(self):
        assert address._clean_for_xlsx("a\x00b") == "ab"


# ===========================================================================
# _volume_table
# ===========================================================================

class TestVolumeTable:
    def _make_df(self):
        return pd.DataFrame({
            "chunk_id": ["p0", "p1", "p2", "p3"],
            "concern": ["a", "b", "a", "c"],
            "technology": ["AI", "Nuclear", "AI", "GM"],
            "year": [2020, 2021, 2022, 2020],
        })

    def test_returns_dataframe(self):
        df = self._make_df()
        result = address._volume_table(df, "concern")
        assert isinstance(result, pd.DataFrame)

    def test_non_empty_result(self):
        df = self._make_df()
        result = address._volume_table(df, "concern")
        assert len(result) > 0


# ===========================================================================
# _top_clusters
# ===========================================================================

class TestTopClusters:
    def test_returns_dataframe(self):
        df = pd.DataFrame({
            "cluster_id": [0, 1, 0, 2, 1],
            "technology_meta": ["AI"] * 5,
        })
        result = address._top_clusters(df, None, "concern")
        assert isinstance(result, pd.DataFrame)


# ===========================================================================
# ai_fingerprint_over_crosscut
# ===========================================================================

class TestAiFingerprintOverCrosscut:
    def test_returns_series(self):
        sal = pd.DataFrame(
            {"AI": [0.5, 0.3, 0.2], "Nuclear": [0.2, 0.4, 0.4]},
            index=[0, 1, 2],
        )
        cross_mask = pd.Series([True, True, False], index=[0, 1, 2])
        result = address.ai_fingerprint_over_crosscut(sal, cross_mask, ai_col="AI")
        assert isinstance(result, pd.Series)
