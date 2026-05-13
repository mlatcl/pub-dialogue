"""
pub_dialogue.access — Data access stage: PDF ingestion, chunking, and artefact loading.

This module owns everything that brings raw data into digital form: reading PDF files,
splitting text into paragraph chunks, and loading pre-computed artefacts from disk for
downstream analysis notebooks.  It has no dependency on the research question and makes
no LLM calls.

Public API:
  Chunking:
    extract_chunks_from_pdf
    reset_chunk_stats, get_chunk_stats
  I/O:
    load_artifacts, save_checkpoint, load_checkpoint
  Private helpers:
    _extract_paragraphs_from_blocks, _paragraph_split
    _split_into_sentences, _repack_sentences_into_chunks

Constants:
  MIN_CHUNK_WORDS, MIN_CHUNK_CHARS, MAX_CHUNK_WORDS
  SENTENCE_FALLBACK_TARGET_WORDS, SENTENCE_FALLBACK_MIN_PARAGRAPHS
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Chunking constants — match v19 notebook configuration
# ---------------------------------------------------------------------------

MIN_CHUNK_WORDS: int = 40
MIN_CHUNK_CHARS: int = 80
MAX_CHUNK_WORDS: int = 500
SENTENCE_FALLBACK_TARGET_WORDS: int = 300
SENTENCE_FALLBACK_MIN_PARAGRAPHS: int = 3

# ---------------------------------------------------------------------------
# Chunk statistics accumulator
# ---------------------------------------------------------------------------

# Module-level accumulator; reset between pipeline runs with reset_chunk_stats().
_chunk_stats: Dict[str, int] = {
    "paragraphs_seen": 0,
    "paragraphs_kept": 0,
    "paragraphs_truncated": 0,
    "paragraphs_below_word_floor": 0,
    "paragraphs_below_char_floor": 0,
    "paragraphs_empty": 0,
    "documents_paragraph_only": 0,
    "documents_paragraph_with_split": 0,
    "documents_sentence_fallback": 0,
    "oversized_paragraphs_split": 0,
    "chunks_from_sentence_split": 0,
    "chunks_from_sentence_fallback": 0,
    "documents_blocks_primary": 0,
    "documents_text_newline_primary": 0,
}


def reset_chunk_stats() -> None:
    """Reset the module-level chunk statistics accumulator to zero."""
    for key in _chunk_stats:
        _chunk_stats[key] = 0


def get_chunk_stats() -> Dict[str, int]:
    """Return a copy of the current chunk statistics accumulator."""
    return dict(_chunk_stats)


# ---------------------------------------------------------------------------
# Private chunking helpers
# ---------------------------------------------------------------------------

def _split_into_sentences(text: str) -> List[str]:
    """Split *text* into sentences. Collapses whitespace first."""
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\d])", text)
    return [p.strip() for p in parts if p.strip()]


def _repack_sentences_into_chunks(sentences: List[str], target_words: int) -> List[str]:
    """Greedily repack *sentences* into chunks of approximately *target_words* words."""
    chunks: List[str] = []
    current: List[str] = []
    current_words = 0
    for sent in sentences:
        sent_words = len(sent.split())
        if sent_words >= target_words:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_words = 0
            chunks.append(sent)
            continue
        if current_words + sent_words > target_words and current:
            chunks.append(" ".join(current))
            current = [sent]
            current_words = sent_words
        else:
            current.append(sent)
            current_words += sent_words
    if current:
        chunks.append(" ".join(current))
    return chunks


def _extract_paragraphs_from_blocks(doc) -> List[str]:
    """Layout-aware paragraph extraction using PyMuPDF's block detection.

    Each text block identified by PyMuPDF (``page.get_text("blocks")``) is
    treated as one paragraph candidate.  This uses the PDF's geometry — gaps
    between runs of text — rather than relying on ``\\n\\n`` being present in
    the text stream.  Works for PDFs where paragraph breaks are implicit in the
    layout but not encoded as double-newlines.

    Block tuples: ``(x0, y0, x1, y1, text, block_no, block_type)``
    ``block_type == 0`` means text; ``block_type == 1`` means image.

    Returns a list of non-empty, whitespace-normalised paragraph strings.
    """
    paragraphs = []
    for page in doc:
        for block in page.get_text("blocks"):
            if block[6] != 0:  # skip image blocks
                continue
            text = re.sub(r"\s+", " ", block[4]).strip()
            if text:
                paragraphs.append(text)
    return paragraphs


def _paragraph_split(full_text: str) -> List[str]:
    """Split *full_text* on double-newlines; return non-empty cleaned paragraphs."""
    paragraphs = re.split(r"\n\s*\n", full_text)
    out = []
    for para in paragraphs:
        para = re.sub(r"\s+", " ", para).strip()
        if para:
            out.append(para)
    return out


# ---------------------------------------------------------------------------
# PDF chunk extraction
# ---------------------------------------------------------------------------

def extract_chunks_from_pdf(
    pdf_path: Path,
    metadata: Dict[str, Any],
    min_chunk_words: int = MIN_CHUNK_WORDS,
    min_chunk_chars: int = MIN_CHUNK_CHARS,
    max_chunk_words: int = MAX_CHUNK_WORDS,
    sentence_fallback_target_words: int = SENTENCE_FALLBACK_TARGET_WORDS,
    sentence_fallback_min_paragraphs: int = SENTENCE_FALLBACK_MIN_PARAGRAPHS,
) -> List[Dict[str, Any]]:
    """Extract text chunks from a single PDF using the v19 three-case hybrid strategy.

    Case 1 — Paragraph-only segmentation:
        Double-newline splitting produces ≥ *sentence_fallback_min_paragraphs*
        substantive paragraphs and no paragraph exceeds *max_chunk_words*.
        All chunks are the author's paragraphs, unchanged.

    Case 2 — Paragraph segmentation with internal sentence-splitting:
        Double-newline splitting produces enough substantive paragraphs but at
        least one paragraph exceeds *max_chunk_words*.  Well-sized paragraphs
        are kept as-is; only the oversized ones are sentence-split into windows
        of ≈ *sentence_fallback_target_words* words.

    Case 3 — Full sentence-level fallback:
        Neither block extraction nor double-newline splitting produces
        *sentence_fallback_min_paragraphs* substantive paragraphs.  The
        entire document is sentence-split and repacked.

    Paragraph detection uses a two-tier approach:

    1. **Blocks-primary** (``page.get_text("blocks")``): uses PyMuPDF's
       layout geometry to identify paragraph boundaries, working even when
       the PDF text stream lacks ``\\n\\n`` encoding.  This is tried first.
    2. **Text-newline fallback** (``_paragraph_split``): splits the full
       plain-text string on double-newlines.  Used only when blocks produce
       fewer than *sentence_fallback_min_paragraphs* substantive segments.

    Each returned chunk dict includes a ``chunking_method`` key:
    ``"paragraph"``, ``"sentence_split"``, or ``"sentence_fallback"``.

    Accumulates statistics into the module-level ``_chunk_stats`` dict.
    Call :func:`reset_chunk_stats` before each pipeline run and
    :func:`get_chunk_stats` to retrieve the totals.

    Parameters
    ----------
    pdf_path:
        Path to the PDF file.
    metadata:
        Dict with at least ``'technology'`` and ``'year'`` keys.
    min_chunk_words, min_chunk_chars, max_chunk_words:
        Length filters applied after chunking.
    sentence_fallback_target_words:
        Target window size (words) when sentence-repacking.
    sentence_fallback_min_paragraphs:
        Minimum substantive paragraphs required for paragraph-mode; fewer
        triggers case-3 sentence fallback.

    Returns
    -------
    list of dicts, one per accepted chunk.
    """
    try:
        import fitz  # type: ignore  # PyMuPDF
    except ImportError as exc:
        raise ImportError("PyMuPDF (fitz) is required for PDF extraction.") from exc

    chunks: List[Dict[str, Any]] = []

    try:
        doc = fitz.open(pdf_path)

        block_paragraphs = _extract_paragraphs_from_blocks(doc)
        full_text = "".join(page.get_text() for page in doc)
        doc.close()

        block_substantive = [
            p for p in block_paragraphs
            if len(p.split()) >= min_chunk_words and len(p) >= min_chunk_chars
        ]
        if len(block_substantive) >= sentence_fallback_min_paragraphs:
            paragraphs = block_paragraphs
            _chunk_stats["documents_blocks_primary"] += 1
        else:
            paragraphs = _paragraph_split(full_text)
            _chunk_stats["documents_text_newline_primary"] += 1

        substantive = [
            p for p in paragraphs
            if len(p.split()) >= min_chunk_words and len(p) >= min_chunk_chars
        ]
        too_few_paragraphs = len(substantive) < sentence_fallback_min_paragraphs

        if too_few_paragraphs:
            # Case 3: full sentence-level fallback
            _chunk_stats["documents_sentence_fallback"] += 1
            sentences = _split_into_sentences(full_text)
            packed = _repack_sentences_into_chunks(sentences, sentence_fallback_target_words)
            chunk_inputs: List[tuple] = [(c, "sentence_fallback") for c in packed]
            _chunk_stats["chunks_from_sentence_fallback"] += len(chunk_inputs)
        else:
            # Cases 1 and 2: paragraph-mode
            chunk_inputs = []
            any_split = False
            for para in paragraphs:
                para = re.sub(r"\s+", " ", para).strip()
                if not para:
                    continue
                if len(para.split()) > max_chunk_words:
                    sentences = _split_into_sentences(para)
                    sub_chunks = _repack_sentences_into_chunks(
                        sentences, sentence_fallback_target_words
                    )
                    for sc in sub_chunks:
                        chunk_inputs.append((sc, "sentence_split"))
                    _chunk_stats["oversized_paragraphs_split"] += 1
                    _chunk_stats["chunks_from_sentence_split"] += len(sub_chunks)
                    any_split = True
                else:
                    chunk_inputs.append((para, "paragraph"))

            if any_split:
                _chunk_stats["documents_paragraph_with_split"] += 1
            else:
                _chunk_stats["documents_paragraph_only"] += 1

        for i, (text, method) in enumerate(chunk_inputs):
            text = re.sub(r"\s+", " ", text).strip()
            _chunk_stats["paragraphs_seen"] += 1

            if not text:
                _chunk_stats["paragraphs_empty"] += 1
                continue
            if len(text.split()) < min_chunk_words:
                _chunk_stats["paragraphs_below_word_floor"] += 1
                continue
            if len(text) < min_chunk_chars:
                _chunk_stats["paragraphs_below_char_floor"] += 1
                continue

            words = text.split()
            was_truncated = False
            if len(words) > max_chunk_words:
                text = " ".join(words[:max_chunk_words])
                was_truncated = True
                _chunk_stats["paragraphs_truncated"] += 1

            chunks.append({
                "text": text,
                "source_file": Path(pdf_path).name,
                "chunk_index": i,
                "word_count": len(text.split()),
                "was_truncated": was_truncated,
                "chunking_method": method,
                "technology": metadata.get("technology", "Unknown"),
                "technology_meta": metadata.get("technology", "Unknown"),
                "year": metadata.get("year", None),
            })
            _chunk_stats["paragraphs_kept"] += 1

    except Exception as e:
        print(f"Error processing {Path(pdf_path).name}: {e}")

    return chunks


# ---------------------------------------------------------------------------
# Checkpoint I/O
# ---------------------------------------------------------------------------

def save_checkpoint(data: Any, checkpoint_path: Path) -> Path:
    """Serialise *data* to JSON at *checkpoint_path*.

    Parameters
    ----------
    data:
        JSON-serialisable object (lists, dicts, strings, numbers).
    checkpoint_path:
        Full path to the output file (including filename and extension).

    Returns
    -------
    Path
        The path the data was written to.
    """
    checkpoint_path = Path(checkpoint_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return checkpoint_path


def load_checkpoint(checkpoint_path: Path) -> Optional[Any]:
    """Load JSON from *checkpoint_path*, or return None if the file does not exist.

    Parameters
    ----------
    checkpoint_path:
        Full path to the checkpoint file.
    """
    checkpoint_path = Path(checkpoint_path)
    if checkpoint_path.exists():
        with open(checkpoint_path) as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------------------
# Artefact loader for analysis notebooks
# ---------------------------------------------------------------------------

def load_artifacts(output_folder: Path, checkpoint_folder: Path) -> dict:
    """Load all pre-computed analysis artifacts from disk.

    Intended for analysis notebooks (02–05) that must boot entirely from saved
    files without calling the OpenAI API or re-running k-means.  Call once at
    the top of each analysis notebook and unpack the returned dict into local
    variables.

    Parameters
    ----------
    output_folder:
        Directory containing CSV/JSON/PNG outputs (typically ``outputs/``).
    checkpoint_folder:
        Directory containing binary checkpoints (``*.npy``, ``*.json``)
        written during processing (typically ``checkpoints/``).

    Returns
    -------
    dict with keys:
        Always present (written by 01_processing.ipynb):
            chunks_df, concerns_df, benefits_df,
            concern_embeddings, concern_ids,
            benefit_embeddings, benefit_ids.
        Optional — ``None`` when 01a_clustering.ipynb has not yet been run:
            concern_centroids, benefit_centroids,
            cluster_labels, cluster_summary_df,
            benefit_cluster_labels, benefit_cluster_summary_df,
            framing_lens_mappings, benefit_framing_lens_mappings,
            cluster_entropy, cluster_entropy_norm, cross_cutting_clusters,
            benefit_cluster_entropy, normalized_entropy_benefits,
            cross_cutting_clusters_benefits.
    """
    out = Path(output_folder)
    ckpt = Path(checkpoint_folder)
    a: Dict[str, Any] = {}

    # --- always present after 01_processing.ipynb ---
    a["chunks_df"]          = pd.read_csv(out / "paragraph_chunks.csv")
    a["concerns_df"]        = pd.read_csv(out / "extracted_concerns.csv")
    a["benefits_df"]        = pd.read_csv(out / "extracted_benefits.csv")

    a["concern_embeddings"] = np.load(ckpt / "concern_embeddings.npy")
    a["benefit_embeddings"] = np.load(ckpt / "benefit_embeddings.npy")

    for name, path in [
        ("concern_ids", ckpt / "concern_ids.json"),
        ("benefit_ids", ckpt / "benefit_ids.json"),
    ]:
        with open(path) as _f:
            a[name] = json.load(_f)

    # --- optional: only present after 01a_clustering.ipynb ---
    def _load_npy(path: Path):
        return np.load(path) if path.exists() else None

    def _load_csv(path: Path):
        return pd.read_csv(path) if path.exists() else None

    def _load_json(path: Path):
        if not path.exists():
            return None
        with open(path) as _f:
            return json.load(_f)

    a["concern_centroids"]          = _load_npy(ckpt / "cluster_centroids.npy")
    a["benefit_centroids"]          = _load_npy(ckpt / "benefit_cluster_centroids.npy")
    a["cluster_summary_df"]         = _load_csv(out  / "cluster_summary.csv")
    a["benefit_cluster_summary_df"] = _load_csv(out  / "benefit_cluster_summary.csv")

    for name, path in [
        ("cluster_labels",                out / "cluster_labels.json"),
        ("benefit_cluster_labels",        out / "benefit_cluster_labels.json"),
        ("framing_lens_mappings",         out / "framing_lens_mappings.json"),
        ("benefit_framing_lens_mappings", out / "benefit_framing_lens_mappings.json"),
    ]:
        a[name] = _load_json(path)

    _ce = _load_json(out / "cluster_entropy.json")
    if _ce is not None:
        a["cluster_entropy"]        = {int(k): v for k, v in _ce["raw"].items()}
        a["cluster_entropy_norm"]   = {int(k): v for k, v in _ce["norm"].items()}
        a["cross_cutting_clusters"] = _ce["cross_cutting"]
    else:
        a["cluster_entropy"] = a["cluster_entropy_norm"] = a["cross_cutting_clusters"] = None

    _bce = _load_json(out / "benefit_cluster_entropy.json")
    if _bce is not None:
        a["benefit_cluster_entropy"]         = {int(k): v for k, v in _bce["raw"].items()}
        a["normalized_entropy_benefits"]     = {int(k): v for k, v in _bce["norm"].items()}
        a["cross_cutting_clusters_benefits"] = _bce["cross_cutting"]
    else:
        a["benefit_cluster_entropy"] = a["normalized_entropy_benefits"] = \
            a["cross_cutting_clusters_benefits"] = None

    return a
