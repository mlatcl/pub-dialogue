"""
pub_dialogue.access — Data access stage: paths, artefact loading, chunking config.

This module owns everything that brings analysis inputs into a usable form for
downstream notebooks: path/config for PDF folders and outputs, and loading
pre-computed artefacts from disk.  It has no dependency on the research
question and makes no LLM calls.

PDF text units are **not** segmented here.  Call lynguine’s document access
API directly (CIP-0015 / REQ-0008)::

    from lynguine.access.documents import segment_pdf_frame

    units = segment_pdf_frame(
        str(pdf_path),
        strategy=access.AccessStage().strategy,  # "pub_dialogue.v1"
        aspect="body_chunks",
        allowed_roots=[str(pdf_folder.resolve())],
        min_chunk_words=40,
        min_chunk_chars=80,
        max_chunk_words=500,
        on_sparse_text="warn",
    )
    # Join research metadata (technology, year) after segmentation.

Public API:
  Stage class (CIP-0010 / CIP-0015):
    AccessStage — typed config dataclass; use AccessStage() in notebook setup cells
  I/O:
    load_artifacts, save_checkpoint, load_checkpoint

Constants (defaults passed through to lynguine ``pub_dialogue.v1``):
  MIN_CHUNK_WORDS, MIN_CHUNK_CHARS, MAX_CHUNK_WORDS
  SENTENCE_FALLBACK_TARGET_WORDS, SENTENCE_FALLBACK_MIN_PARAGRAPHS
  MIN_TEXT_COVERAGE, DEFAULT_SEGMENT_STRATEGY, DEFAULT_ON_SPARSE_TEXT
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Chunking defaults — match lynguine pub_dialogue.v1 / prior v19 config
# ---------------------------------------------------------------------------

MIN_CHUNK_WORDS: int = 40
MIN_CHUNK_CHARS: int = 80
MAX_CHUNK_WORDS: int = 500
SENTENCE_FALLBACK_TARGET_WORDS: int = 300
SENTENCE_FALLBACK_MIN_PARAGRAPHS: int = 3
MIN_TEXT_COVERAGE: float = 0.5
DEFAULT_SEGMENT_STRATEGY: str = "pub_dialogue.v1"
DEFAULT_ON_SPARSE_TEXT: str = "warn"

# ---------------------------------------------------------------------------
# AccessStage — typed config dataclass (CIP-0010 / CIP-0015)
# ---------------------------------------------------------------------------

@dataclass
class AccessStage:
    """Configuration and entry-point for the Access pipeline stage.

    Centralises path and lynguine chunking knobs that were previously repeated
    in every notebook setup cell.  PDF segmentation is performed by calling
    ``lynguine.access.documents.segment_pdf_frame`` with these fields — this
    class does not wrap or re-implement the chunker.

    Usage in notebook setup cells::

        from pub_dialogue.access import AccessStage
        access = AccessStage()          # use defaults
        a = access.load_artifacts()     # load pre-computed outputs
    """

    output_folder: Path = field(default_factory=lambda: Path("outputs"))
    checkpoint_folder: Path = field(default_factory=lambda: Path("checkpoints"))
    pdf_folder: Path = field(default_factory=lambda: Path("pdfs"))
    strategy: str = DEFAULT_SEGMENT_STRATEGY
    on_sparse_text: str = DEFAULT_ON_SPARSE_TEXT
    min_chunk_words: int = MIN_CHUNK_WORDS
    max_chunk_words: int = MAX_CHUNK_WORDS
    min_chunk_chars: int = MIN_CHUNK_CHARS
    sentence_fallback_target_words: int = SENTENCE_FALLBACK_TARGET_WORDS
    sentence_fallback_min_paragraphs: int = SENTENCE_FALLBACK_MIN_PARAGRAPHS
    min_text_coverage: float = MIN_TEXT_COVERAGE
    filter_chrome: bool = False

    def load_artifacts(self) -> dict:
        """Load pre-computed artefacts from output_folder and checkpoint_folder."""
        return load_artifacts(self.output_folder, self.checkpoint_folder)

    def segment_kwargs(self) -> Dict[str, Any]:
        """Keyword arguments for ``segment_pdf`` / ``segment_pdf_frame``.

        Does not include ``path`` or ``allowed_roots`` (caller-specific).
        """
        return {
            "strategy": self.strategy,
            "aspect": "body_chunks",
            "on_sparse_text": self.on_sparse_text,
            "min_chunk_words": self.min_chunk_words,
            "min_chunk_chars": self.min_chunk_chars,
            "max_chunk_words": self.max_chunk_words,
            "sentence_fallback_target_words": self.sentence_fallback_target_words,
            "sentence_fallback_min_paragraphs": self.sentence_fallback_min_paragraphs,
            "min_text_coverage": self.min_text_coverage,
            "filter_chrome": self.filter_chrome,
        }


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
    a["benefit_centroids"]          = _load_npy(ckpt / "cluster_centroids_benefit.npy")
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
