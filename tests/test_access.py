"""
tests/test_access.py — tests for pub_dialogue.access (CIP-0015).

Chunking algorithm tests live upstream in lynguine.  Here we cover AccessStage
config, checkpoint I/O, artefact loading smoke, and the lynguine integration
contract (no local chunker; segment_pdf_frame importable).
"""

from pathlib import Path

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

    def test_default_strategy_is_pub_dialogue_v1(self):
        assert access.DEFAULT_SEGMENT_STRATEGY == "pub_dialogue.v1"

    def test_default_on_sparse_text(self):
        assert access.DEFAULT_ON_SPARSE_TEXT in {"warn", "error", "empty"}


# ===========================================================================
# No local chunker (REQ-0008 / CIP-0015)
# ===========================================================================

class TestNoLocalChunker:
    def test_extract_chunks_from_pdf_not_defined(self):
        assert not hasattr(access, "extract_chunks_from_pdf")

    def test_chunk_helpers_not_exported(self):
        for name in (
            "_split_into_sentences",
            "_repack_sentences_into_chunks",
            "_extract_paragraphs_from_blocks",
            "_paragraph_split",
            "reset_chunk_stats",
            "get_chunk_stats",
            "get_doc_diagnostics",
        ):
            assert not hasattr(access, name)


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
# AccessStage dataclass
# ===========================================================================

class TestAccessStageDefaults:
    def test_output_folder_default(self):
        stage = access.AccessStage()
        assert stage.output_folder == Path("outputs")

    def test_checkpoint_folder_default(self):
        stage = access.AccessStage()
        assert stage.checkpoint_folder == Path("checkpoints")

    def test_pdf_folder_default(self):
        stage = access.AccessStage()
        assert stage.pdf_folder == Path("pdfs")

    def test_strategy_default(self):
        stage = access.AccessStage()
        assert stage.strategy == access.DEFAULT_SEGMENT_STRATEGY

    def test_on_sparse_text_default(self):
        stage = access.AccessStage()
        assert stage.on_sparse_text == access.DEFAULT_ON_SPARSE_TEXT

    def test_min_chunk_words_matches_module_constant(self):
        stage = access.AccessStage()
        assert stage.min_chunk_words == access.MIN_CHUNK_WORDS

    def test_max_chunk_words_matches_module_constant(self):
        stage = access.AccessStage()
        assert stage.max_chunk_words == access.MAX_CHUNK_WORDS

    def test_min_chunk_chars_matches_module_constant(self):
        stage = access.AccessStage()
        assert stage.min_chunk_chars == access.MIN_CHUNK_CHARS

    def test_no_ocr_if_image_only_field(self):
        assert "ocr_if_image_only" not in access.AccessStage.__dataclass_fields__

    def test_fields_are_overridable(self):
        stage = access.AccessStage(output_folder=Path("custom_out"))
        assert stage.output_folder == Path("custom_out")

    def test_segment_kwargs_includes_strategy(self):
        kw = access.AccessStage().segment_kwargs()
        assert kw["strategy"] == "pub_dialogue.v1"
        assert kw["aspect"] == "body_chunks"
        assert "path" not in kw
        assert "allowed_roots" not in kw

    def test_load_artifacts_delegates(self, tmp_path):
        stage = access.AccessStage(
            output_folder=tmp_path, checkpoint_folder=tmp_path
        )
        with pytest.raises((FileNotFoundError, Exception)):
            stage.load_artifacts()


# ===========================================================================
# load_artifacts smoke
# ===========================================================================

class TestLoadArtifactsSmoke:
    def test_load_artifacts_raises_on_missing_files(self, tmp_path):
        with pytest.raises((FileNotFoundError, Exception)):
            access.load_artifacts(tmp_path, tmp_path)


# ===========================================================================
# Lynguine integration contract
# ===========================================================================

class TestLynguineDocumentAccess:
    def test_segment_pdf_frame_importable(self):
        from lynguine.access.documents import segment_pdf_frame

        assert callable(segment_pdf_frame)

    def test_pub_dialogue_v1_registered(self):
        from lynguine.access.documents import ensure_builtin_strategies, list_strategies

        ensure_builtin_strategies()
        assert "pub_dialogue.v1" in list_strategies()

    def test_segment_pdf_frame_on_fixture_pdf(self, tmp_path):
        """Integration: one small PDF through lynguine with AccessStage knobs."""
        fitz = pytest.importorskip("fitz")
        from lynguine.access.documents import segment_pdf_frame

        pdf = tmp_path / "tiny.pdf"
        doc = fitz.open()
        page = doc.new_page()
        # Enough words to pass min floors after block/newline segmentation
        para = " ".join(["word"] * 50)
        page.insert_text((72, 72), "\n\n".join([para] * 4))
        doc.save(pdf)
        doc.close()

        stage = access.AccessStage(pdf_folder=tmp_path)
        units = segment_pdf_frame(
            str(pdf),
            allowed_roots=[str(tmp_path.resolve())],
            **stage.segment_kwargs(),
        )
        assert "unit_id" in units.columns
        assert "text" in units.columns
        assert "source_path" in units.columns
        assert len(units) >= 1
