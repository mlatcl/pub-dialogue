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

# ===========================================================================
# AccessStage dataclass (CIP-0010 Phase 1)
# ===========================================================================

class TestAccessStageDefaults:
    """Verify AccessStage defaults match the constants used across notebooks."""

    def test_output_folder_default(self):
        stage = access.AccessStage()
        assert stage.output_folder == Path("outputs")

    def test_checkpoint_folder_default(self):
        stage = access.AccessStage()
        assert stage.checkpoint_folder == Path("checkpoints")

    def test_pdf_folder_default(self):
        stage = access.AccessStage()
        assert stage.pdf_folder == Path("pdfs")

    def test_min_chunk_words_matches_module_constant(self):
        stage = access.AccessStage()
        assert stage.min_chunk_words == access.MIN_CHUNK_WORDS

    def test_max_chunk_words_matches_module_constant(self):
        stage = access.AccessStage()
        assert stage.max_chunk_words == access.MAX_CHUNK_WORDS

    def test_min_chunk_chars_matches_module_constant(self):
        stage = access.AccessStage()
        assert stage.min_chunk_chars == access.MIN_CHUNK_CHARS

    def test_fields_are_overridable(self):
        stage = access.AccessStage(output_folder=Path("custom_out"))
        assert stage.output_folder == Path("custom_out")

    def test_load_artifacts_delegates(self, tmp_path):
        stage = access.AccessStage(
            output_folder=tmp_path, checkpoint_folder=tmp_path
        )
        with pytest.raises((FileNotFoundError, Exception)):
            stage.load_artifacts()


# ===========================================================================
# load_artifacts (basic smoke test — detailed tests in test_dialogue_utils)
# ===========================================================================

class TestLoadArtifactsSmoke:
    def test_load_artifacts_raises_on_missing_files(self, tmp_path):
        with pytest.raises((FileNotFoundError, Exception)):
            access.load_artifacts(tmp_path, tmp_path)


# ===========================================================================
# Coverage-based fallback and image-only detection
# ===========================================================================
 
import pytest as _pytest
 
_PARA = ("Participants worried that decisions about their data would be made "
         "without them, and asked who would be accountable when things went "
         "wrong. They wanted clear explanations, independent oversight and a "
         "meaningful way to say no. ")
 
 
def _make_pdf(path, paragraphs, fragments=0, fragment_text=None):
    """Build a real PDF: each paragraph in its own text box (one layout block),
    followed by *fragments* short one-line boxes (e.g. bullets / table cells)."""
    fitz = _pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page()
    y = 40
    for p in paragraphs:
        if y > 700:
            page, y = doc.new_page(), 40
        page.insert_textbox(fitz.Rect(40, y, 560, y + 150), p, fontsize=9)
        y += 160
    for i in range(fragments):
        if y > 780:
            page, y = doc.new_page(), 40
        txt = fragment_text or f"Point {i}: people said they want fair rules and more control over data use here."
        page.insert_textbox(fitz.Rect(40, y, 560, y + 14), txt, fontsize=8)
        y += 22
    doc.save(str(path))
    doc.close()
 
 
class TestCoverageFallback:
    def _run(self, path, **kw):
        access.reset_chunk_stats()
        chunks = access.extract_chunks_from_pdf(path, {"technology": "AI", "year": 2024}, **kw)
        return chunks, access.get_doc_diagnostics().iloc[0]
 
    def test_well_formed_document_keeps_paragraph_mode(self, tmp_path):
        pdf = tmp_path / "clean.pdf"
        _make_pdf(pdf, [_PARA * 2] * 5)
        chunks, d = self._run(pdf)
        assert d["segmentation"] == "blocks"
        assert not d["low_coverage_fallback"]
        assert all(c["chunking_method"] == "paragraph" for c in chunks)
        assert d["final_coverage"] > 0.9
 
    def test_fragmented_document_triggers_sentence_fallback(self, tmp_path):
        # 3 real paragraphs (passes the old paragraph-count test) plus 120
        # short bullet lines that the 40-word floor would discard.
        pdf = tmp_path / "fragmented.pdf"
        _make_pdf(pdf, [_PARA * 2] * 3, fragments=120)
        chunks, d = self._run(pdf)
        assert d["blocks_coverage"] < 0.5
        assert d["low_coverage_fallback"]
        assert d["segmentation"] == "sentence"
        assert all(c["chunking_method"] == "sentence_fallback" for c in chunks)
        assert d["final_coverage"] > 0.9
        assert access.get_chunk_stats()["documents_low_coverage_fallback"] == 1
 
    def test_zero_threshold_reproduces_v19_behaviour(self, tmp_path):
        pdf = tmp_path / "fragmented.pdf"
        _make_pdf(pdf, [_PARA * 2] * 3, fragments=120)
        chunks, d = self._run(pdf, min_text_coverage=0.0)
        assert d["segmentation"] == "blocks"
        assert len(chunks) == 3            # only the three real paragraphs survive
        assert d["final_coverage"] < 0.5   # most text silently lost
 
    def test_fallback_recovers_more_text_than_v19(self, tmp_path):
        pdf = tmp_path / "fragmented.pdf"
        _make_pdf(pdf, [_PARA * 2] * 3, fragments=120)
        _, old = self._run(pdf, min_text_coverage=0.0)
        _, new = self._run(pdf)
        assert new["words_kept"] > 2 * old["words_kept"]
 
    def test_diagnostics_columns(self, tmp_path):
        pdf = tmp_path / "clean.pdf"
        _make_pdf(pdf, [_PARA * 2] * 4)
        _, d = self._run(pdf)
        for col in ["pages", "total_words", "words_per_page", "likely_image_only",
                    "ocr_applied", "blocks_coverage", "newline_coverage", "fallback_reason",
                    "segmentation", "low_coverage_fallback", "chunks_kept",
                    "words_kept", "final_coverage"]:
            assert col in d.index
 
    def test_reset_clears_diagnostics(self, tmp_path):
        pdf = tmp_path / "clean.pdf"
        _make_pdf(pdf, [_PARA * 2] * 4)
        self._run(pdf)
        access.reset_chunk_stats()
        assert access.get_doc_diagnostics().empty
 
 
class TestImageOnlyDetection:
    def _image_only_pdf(self, path):
        fitz = _pytest.importorskip("fitz")
        src = fitz.open()
        page = src.new_page()
        page.insert_textbox(fitz.Rect(40, 40, 560, 800), _PARA * 6, fontsize=11)
        pix = page.get_pixmap(dpi=200)
        src.close()
        doc = fitz.open()
        out = doc.new_page()
        out.insert_image(out.rect, pixmap=pix)
        doc.save(str(path))
        doc.close()
 
    def test_image_only_pdf_is_flagged(self, tmp_path):
        pdf = tmp_path / "scan.pdf"
        self._image_only_pdf(pdf)
        access.reset_chunk_stats()
        chunks = access.extract_chunks_from_pdf(pdf, {})
        d = access.get_doc_diagnostics().iloc[0]
        assert bool(d["likely_image_only"])
        assert not bool(d["ocr_applied"])
        assert chunks == []
        assert access.get_chunk_stats()["documents_likely_image_only"] == 1
 
    def test_ocr_recovers_text_when_tesseract_available(self, tmp_path):
        import shutil
        if shutil.which("tesseract") is None:
            _pytest.skip("Tesseract not installed")
        pdf = tmp_path / "scan.pdf"
        self._image_only_pdf(pdf)
        access.reset_chunk_stats()
        chunks = access.extract_chunks_from_pdf(pdf, {}, ocr_if_image_only=True)
        d = access.get_doc_diagnostics().iloc[0]
        if not bool(d["ocr_applied"]):
            _pytest.skip("Tesseract present but tessdata not found by PyMuPDF")
        assert len(chunks) >= 1
        assert "accountable" in " ".join(c["text"] for c in chunks)
 
