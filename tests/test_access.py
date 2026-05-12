"""
tests/test_access.py — tests for pub_dialogue.access module.

Covers module-level constants, chunk-stat helpers, checkpoint I/O, and the
chunking pipeline functions.  Functions already tested via test_dialogue_utils
(load_artifacts, extract_chunks_from_pdf) are not duplicated here.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import pub_dialogue.access as access


# ===========================================================================
# Constants exported by the module
# ===========================================================================

class TestAccessConstants:
    def test_min_chunk_words_positive(self):
        assert access.MIN_CHUNK_WORDS > 0

    def test_min_chunk_chars_positive(self):
        assert access.MIN_CHUNK_CHARS > 0

    def test_max_chunk_words_greater_than_min(self):
        assert access.MAX_CHUNK_WORDS > access.MIN_CHUNK_WORDS

    def test_sentence_fallback_target_words_positive(self):
        assert access.SENTENCE_FALLBACK_TARGET_WORDS > 0

    def test_sentence_fallback_min_paragraphs_positive(self):
        assert access.SENTENCE_FALLBACK_MIN_PARAGRAPHS > 0


# ===========================================================================
# Chunk statistics helpers
# ===========================================================================

class TestChunkStats:
    def setup_method(self):
        access.reset_chunk_stats()

    def test_reset_zeros_all_counters(self):
        stats = access.get_chunk_stats()
        for v in stats.values():
            assert v == 0

    def test_get_chunk_stats_returns_dict(self):
        assert isinstance(access.get_chunk_stats(), dict)

    def test_stats_contain_expected_keys(self):
        keys = access.get_chunk_stats().keys()
        for expected in ("paragraphs_seen", "paragraphs_kept"):
            assert expected in keys


# ===========================================================================
# Checkpoint I/O
# ===========================================================================

class TestCheckpointIO:
    def test_save_and_load_roundtrip(self, tmp_path):
        data = {"key": [1, 2, 3]}
        path = tmp_path / "checkpoint.json"
        saved = access.save_checkpoint(data, path)
        loaded = access.load_checkpoint(saved)
        assert loaded == data

    def test_load_returns_none_for_missing(self, tmp_path):
        result = access.load_checkpoint(tmp_path / "nonexistent.json")
        assert result is None

    def test_save_returns_path(self, tmp_path):
        result = access.save_checkpoint({"x": 1}, tmp_path / "out.json")
        assert isinstance(result, Path)
        assert result.exists()


# ===========================================================================
# Sentence splitter
# ===========================================================================

class TestSplitIntoSentences:
    def test_splits_on_period_space_capital(self):
        sentences = access._split_into_sentences("Hello world. This is a test.")
        assert len(sentences) >= 2

    def test_empty_string_returns_empty(self):
        assert access._split_into_sentences("") == []

    def test_single_sentence_no_split(self):
        result = access._split_into_sentences("Just one sentence here")
        assert len(result) == 1

    def test_returns_list_of_strings(self):
        result = access._split_into_sentences("A. B. C.")
        assert all(isinstance(s, str) for s in result)


# ===========================================================================
# Sentence repacker
# ===========================================================================

class TestRepackSentences:
    def test_short_sentences_merged_under_target(self):
        sentences = ["Short."] * 10
        chunks = access._repack_sentences_into_chunks(sentences, target_words=100)
        assert len(chunks) >= 1
        assert all(isinstance(c, str) for c in chunks)

    def test_empty_input(self):
        assert access._repack_sentences_into_chunks([], target_words=100) == []


# ===========================================================================
# load_artifacts (basic smoke test — detailed tests in test_dialogue_utils)
# ===========================================================================

class TestLoadArtifactsSmoke:
    def test_load_artifacts_raises_on_missing_files(self, tmp_path):
        with pytest.raises((FileNotFoundError, Exception)):
            access.load_artifacts(tmp_path, tmp_path)
