"""
dialogue_utils.py — Shared utilities for the public dialogue analyser pipeline.

This module consolidates all helper functions that were previously duplicated
across concern and benefit sections of the notebook. The notebook imports this
module and calls functions via `import dialogue_utils as du`.

Public API (grouped by responsibility):
  I/O & display:
    show_status, show_complete, show_warning
    save_checkpoint, load_checkpoint, load_artifacts
  Corpus ingestion:
    extract_chunks_from_pdf
    reset_chunk_stats, get_chunk_stats
    _extract_paragraphs_from_blocks, _paragraph_split
  Extraction:
    ExtractionResult (dataclass)
    extract_phrases
    validate_extraction_cache
  Embeddings:
    filter_missing_source_text
    get_embeddings_batch
  Cluster semantics:
    label_cluster, pretty_label
    clusters_to_labels, clusters_to_lenses, html_escape
  Utilities:
    normalized_entropy, hhi, topk_share, parse_year, tokenize
  Metrics:
    is_privacy_text, entropy_by_year, ai_fingerprint_over_crosscut
  Sensitivity:
    run_sensitivity
  Comparison helpers:
    _volume_table, _top_clusters

Constants:
  META_VOCABULARY              — meta-vocabulary stop-list for CIP-0004 diagnostics
  PRIVACY_TERMS                — keywords for privacy-cluster detection
  CROSSCUTTING_ENTROPY_THRESHOLD — normalised entropy threshold for cross-cutting classification
  EXTRACTION_PROMPT            — LLM prompt template for concern extraction
  BENEFIT_EXTRACTION_PROMPT    — LLM prompt template for benefit extraction
"""

from __future__ import annotations

import html as _html
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Threshold for classifying a cluster as cross-cutting vs. technology-specific.
# A cluster whose normalised technology entropy meets or exceeds this value is
# considered cross-cutting (i.e. present across many technologies rather than
# concentrated in one). 0.5 = at least half of maximum possible entropy.
CROSSCUTTING_ENTROPY_THRESHOLD: float = 0.5

META_VOCABULARY: List[str] = [
    "public dialogue",
    "dialogue participants",
    "public engagement",
    "engagement process",
    "dialogue process",
    "public consultation",
    "stakeholder engagement",
    "public involvement",
    "public participation",
]

PRIVACY_TERMS: List[str] = [
    "privacy", "private", "personal data", "personal information",
    "data protection", "gdpr", "consent", "permission", "surveillance",
    "monitoring", "tracking", "profile", "profiling", "identif", "anonym",
    "de-anonym", "re-identif", "biometric", "face recognition",
    "facial recognition", "cctv", "data sharing", "data use", "data misuse",
    "data breach", "leak", "cyber", "security", "hacking",
]

_PRIVACY_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in PRIVACY_TERMS) + r")\b",
    flags=re.IGNORECASE,
)

EXTRACTION_PROMPT = """Extract the core public concerns from this paragraph.

CRITICAL RULES:
1. Remove ALL technology-specific references (AI, nuclear, genetic, nano, etc.)
2. Extract the underlying concern that could apply to ANY technology
3. Keep phrases concise (3-10 words each)
4. Focus on what people are worried about, not factual statements
5. Do NOT use the words 'public dialogue', 'dialogue', 'engagement',
   'consultation', or 'participation' in your extracted phrases.

EXAMPLES:
- "People worried about AI making unfair decisions" → "unfair automated decisions"
- "Concerns about nuclear waste storage" → "long-term waste storage safety"
- "Distrust of government handling of genetic data" → "distrust of government data handling"

Return 1-3 concern phrases, one per line. No bullets, no numbering.
If the paragraph contains no clear public concern, return "NO_CONCERN".

Paragraph:
{text}"""

BENEFIT_EXTRACTION_PROMPT = """Extract the core public BENEFITS (upsides, hoped-for gains, opportunities) \
from this paragraph.

CRITICAL RULES:
1. Remove ALL technology-specific references (AI, nuclear, genetic, nano, etc.)
2. Extract the underlying benefit that could apply to ANY emerging technology
3. Keep each benefit phrase concise (3-10 words)
4. Prefer concrete impacts over vague praise (e.g., "faster diagnosis" not "innovation")
5. Do NOT include concerns, caveats, or neutral facts unless they clearly express a benefit
6. Do NOT use the words 'public dialogue', 'dialogue', 'engagement',
   'consultation', or 'participation' in your extracted phrases.

EXAMPLES:
- "AI could help doctors spot cancers earlier" → "earlier disease detection"
- "Nuclear could provide reliable low-carbon energy" → "reliable low-carbon energy supply"
- "Robots could take on dangerous tasks" → "reduced human exposure to danger"

Return 1-3 benefit phrases, one per line. No bullets, no numbering.
If the paragraph contains no clear public benefit, return "NO_BENEFIT".

Paragraph:
{text}"""

_SENTINELS = {"NO_CONCERN", "NO_BENEFIT"}

# Chunking defaults — match v19 notebook configuration
MIN_CHUNK_WORDS: int = 40
MIN_CHUNK_CHARS: int = 80
MAX_CHUNK_WORDS: int = 500
SENTENCE_FALLBACK_TARGET_WORDS: int = 300
SENTENCE_FALLBACK_MIN_PARAGRAPHS: int = 3

# Default tech-word filter (can be overridden at call site)
DEFAULT_TECH_WORDS: List[str] = [
    "ai", "artificial intelligence", "nuclear", "genetic", "nano",
    "genome", "robot", "drone", "quantum", "gm", "embryo", "stem cell",
    "neural", "brain-computer",
]

# ---------------------------------------------------------------------------
# I/O & display helpers
# ---------------------------------------------------------------------------

def show_status(msg: str) -> None:
    """Display a blue in-progress message. Degrades gracefully outside Colab."""
    try:
        from IPython.display import HTML, display  # type: ignore
        display(HTML(
            f"<div style='color: #1a73e8; font-weight: bold;'>"
            f"🔄 [{datetime.now().strftime('%H:%M:%S')}] {msg}</div>"
        ))
    except ImportError:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def show_complete(msg: str) -> None:
    """Display a green completion message."""
    try:
        from IPython.display import HTML, display  # type: ignore
        display(HTML(
            f"<div style='color: #0f9d58; font-weight: bold;'>"
            f"✅ [{datetime.now().strftime('%H:%M:%S')}] {msg}</div>"
        ))
    except ImportError:
        print(f"✓ [{datetime.now().strftime('%H:%M:%S')}] {msg}")


def show_warning(msg: str) -> None:
    """Display an amber warning message."""
    try:
        from IPython.display import HTML, display  # type: ignore
        display(HTML(
            f"<div style='color: #f9ab00; font-weight: bold;'>"
            f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] {msg}</div>"
        ))
    except ImportError:
        print(f"⚠ [{datetime.now().strftime('%H:%M:%S')}] {msg}")


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
        chunks_df, concerns_df, benefits_df,
        concern_embeddings, concern_ids,
        benefit_embeddings, benefit_ids,
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

    # DataFrames from CSV
    a["chunks_df"]   = pd.read_csv(out / "paragraph_chunks.csv")
    a["concerns_df"] = pd.read_csv(out / "extracted_concerns.csv")
    a["benefits_df"] = pd.read_csv(out / "extracted_benefits.csv")
    a["cluster_summary_df"]         = pd.read_csv(out / "cluster_summary.csv")
    a["benefit_cluster_summary_df"] = pd.read_csv(out / "benefit_cluster_summary.csv")

    # Numpy arrays from checkpoints
    a["concern_embeddings"]  = np.load(ckpt / "concern_embeddings.npy")
    a["benefit_embeddings"]  = np.load(ckpt / "benefit_embeddings.npy")
    a["concern_centroids"]   = np.load(ckpt / "cluster_centroids.npy")
    a["benefit_centroids"]   = np.load(ckpt / "benefit_cluster_centroids.npy")

    # JSON files — ids and mappings
    for name, path in [
        ("concern_ids",                   ckpt / "concern_ids.json"),
        ("benefit_ids",                   ckpt / "benefit_ids.json"),
        ("cluster_labels",                out  / "cluster_labels.json"),
        ("benefit_cluster_labels",        out  / "benefit_cluster_labels.json"),
        ("framing_lens_mappings",         out  / "framing_lens_mappings.json"),
        ("benefit_framing_lens_mappings", out  / "benefit_framing_lens_mappings.json"),
    ]:
        with open(path) as _f:
            a[name] = json.load(_f)

    # Entropy dicts (written by 01_processing.ipynb via add-entropy-saves task)
    with open(out / "cluster_entropy.json") as _f:
        _d = json.load(_f)
        a["cluster_entropy"]        = {int(k): v for k, v in _d["raw"].items()}
        a["cluster_entropy_norm"]   = {int(k): v for k, v in _d["norm"].items()}
        a["cross_cutting_clusters"] = _d["cross_cutting"]

    with open(out / "benefit_cluster_entropy.json") as _f:
        _d = json.load(_f)
        a["benefit_cluster_entropy"]         = {int(k): v for k, v in _d["raw"].items()}
        a["normalized_entropy_benefits"]     = {int(k): v for k, v in _d["norm"].items()}
        a["cross_cutting_clusters_benefits"] = _d["cross_cutting"]

    return a


# ---------------------------------------------------------------------------
# Corpus ingestion — v19 three-case hybrid chunker
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
    # paragraph-source tracking (v20)
    "documents_blocks_primary": 0,       # blocks mode produced enough paragraphs
    "documents_text_newline_primary": 0, # fell back to double-newline text split
}


def reset_chunk_stats() -> None:
    """Reset the module-level chunk statistics accumulator to zero."""
    for key in _chunk_stats:
        _chunk_stats[key] = 0


def get_chunk_stats() -> Dict[str, int]:
    """Return a copy of the current chunk statistics accumulator."""
    return dict(_chunk_stats)


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

        # Extract both block paragraphs and plain text in a single pass so the
        # doc only needs to be opened once.
        block_paragraphs = _extract_paragraphs_from_blocks(doc)
        full_text = "".join(page.get_text() for page in doc)
        doc.close()

        # Primary paragraph source: PyMuPDF layout blocks (geometry-aware).
        # Falls back to double-newline text splitting for PDFs where the blocks
        # API returns very few segments (e.g. single-column scans presented as
        # one huge block).
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
            # Cases 1 and 2: paragraph-mode, with sentence-splitting only for
            # individual oversized paragraphs.
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

        # Apply floor and cap to all chunks regardless of how they were produced
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
                # Safety net: should not normally fire for sentence-split chunks
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
# Extraction — ExtractionResult dataclass + unified extract_phrases
# ---------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    """Structured result from a single paragraph extraction call.

    Attributes
    ----------
    chunk_id:
        Identifier of the source paragraph chunk.
    raw_phrases:
        Phrases returned by the LLM before any filtering.
    retained_phrases:
        Phrases that passed the tech-word filter.
    dropped_by_filter:
        Phrases removed by the tech-word filter, each paired with the
        matching tech-word substring as (phrase, matching_word) tuples.
    sentinel_returned:
        True when the LLM returned NO_CONCERN or NO_BENEFIT (and no
        other content).
    error:
        Exception message if an API error occurred; None on success.
    """

    chunk_id: str
    raw_phrases: List[str] = field(default_factory=list)
    retained_phrases: List[str] = field(default_factory=list)
    dropped_by_filter: List[tuple] = field(default_factory=list)
    sentinel_returned: bool = False
    error: Optional[str] = None


def extract_phrases(
    row_tuple,
    kind: str,
    client,
    tech_words: Optional[List[str]] = None,
    model: str = "gpt-4o-mini",
    max_tokens: int = 500,
) -> ExtractionResult:
    """Extract decontextualised concern or benefit phrases from one paragraph.

    Unified replacement for the notebook's ``extract_concerns_from_paragraph``
    and ``extract_benefits_from_paragraph`` functions.

    Parameters
    ----------
    row_tuple:
        ``(idx, row)`` tuple where ``row`` is a pandas Series with at least
        ``'chunk_id'`` and ``'text'`` fields.
    kind:
        ``'concern'`` or ``'benefit'``.
    client:
        Initialised OpenAI client.
    tech_words:
        Substring filter list. Defaults to DEFAULT_TECH_WORDS.
    model:
        OpenAI model name.
    max_tokens:
        Maximum completion tokens.

    Returns
    -------
    ExtractionResult
    """
    if kind not in ("concern", "benefit"):
        raise ValueError(f"kind must be 'concern' or 'benefit', got {kind!r}")

    if tech_words is None:
        tech_words = DEFAULT_TECH_WORDS

    _, row = row_tuple
    chunk_id = row["chunk_id"]
    sentinel = "NO_CONCERN" if kind == "concern" else "NO_BENEFIT"
    prompt_template = EXTRACTION_PROMPT if kind == "concern" else BENEFIT_EXTRACTION_PROMPT
    system_msg = (
        "Extract public concerns. Be concise. Remove technology-specific language."
        if kind == "concern"
        else "Extract public benefits. Be concise. Remove technology-specific language."
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt_template.format(text=str(row["text"])[:2000])},
            ],
            max_completion_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        if content is None:
            return ExtractionResult(chunk_id=chunk_id, sentinel_returned=True)

        content = content.strip()

        # Guard against model refusing due to missing text
        if "I don't have the text" in content:
            return ExtractionResult(chunk_id=chunk_id, sentinel_returned=True)

        if content in _SENTINELS or not content:
            return ExtractionResult(chunk_id=chunk_id, sentinel_returned=True)

        raw_phrases = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and line.strip() not in _SENTINELS
        ]

        retained: List[str] = []
        dropped: List[tuple] = []
        for phrase in raw_phrases:
            phrase_lower = phrase.lower()
            match = next(
                (tw for tw in tech_words
                 if re.search(r"\b" + re.escape(tw) + r"\b", phrase_lower)),
                None,
            )
            if match:
                dropped.append((phrase, match))
            else:
                retained.append(phrase)

        return ExtractionResult(
            chunk_id=chunk_id,
            raw_phrases=raw_phrases,
            retained_phrases=retained,
            dropped_by_filter=dropped,
            sentinel_returned=False,
        )

    except Exception as exc:
        return ExtractionResult(
            chunk_id=chunk_id,
            error=f"{type(exc).__name__}: {exc}",
        )


def validate_extraction_cache(cache: Dict[str, Any], kind: str, warn_threshold: float = 0.30) -> bool:
    """Check a loaded extraction cache for signs of a partial-failure run.

    Parameters
    ----------
    cache:
        Mapping of ``chunk_id → list[phrase]`` as loaded from JSON.
    kind:
        ``'concern'`` or ``'benefit'``, used only in warning messages.
    warn_threshold:
        If the fraction of empty entries exceeds this value, print a warning
        and return ``False``.  Default 0.30 (30%).

    Returns
    -------
    bool
        ``True`` if the cache looks complete, ``False`` if suspiciously many
        entries are empty (possibly masked API errors).
    """
    if not cache:
        return False
    n_empty = sum(1 for v in cache.values() if not v)
    frac_empty = n_empty / len(cache)
    if frac_empty > warn_threshold:
        print(
            f"[WARN] {kind} cache: {n_empty}/{len(cache)} entries "
            f"({frac_empty:.0%}) are empty lists."
        )
        print(
            "[WARN] This may indicate a partial-failure run where API errors "
            "were cached as empty. Consider deleting the cache file and "
            "re-running extraction."
        )
        return False
    return True


def write_extraction_diagnostics(
    results: List["ExtractionResult"],
    kind: str,
    output_folder: Path,
) -> None:
    """Write yield-diagnostic files after an extraction pass.

    Produces three files in *output_folder*:

    * ``extraction_yield_summary.csv`` — one row per (kind, run) with counts
      of sentinels, filter drops, errors, and retained phrases.
    * ``tech_filter_drops_{kind}.csv`` — one row per dropped phrase with the
      matching tech-word substring.  Useful for checking filter over-reach.
    * ``extraction_errors_{kind}.log`` — one row per chunk that raised an
      exception during the API call.

    Parameters
    ----------
    results:
        List of :class:`ExtractionResult` objects from a completed extraction.
    kind:
        ``"concern"`` or ``"benefit"``.
    output_folder:
        Directory where output files are written.
    """
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    sentinel_chunks = sum(1 for r in results if r.sentinel_returned)
    error_chunks = sum(1 for r in results if r.error is not None)
    filter_drop_chunks = sum(1 for r in results if r.dropped_by_filter)
    filter_drops_total = sum(len(r.dropped_by_filter) for r in results)
    retained_total = sum(len(r.retained_phrases) for r in results)
    total_chunks = len(results)

    # --- yield summary (append so concern + benefit rows coexist) ---
    summary_path = output_folder / "extraction_yield_summary.csv"
    summary_row = {
        "track": kind,
        "total_chunks": total_chunks,
        "sentinel_empties": sentinel_chunks,
        "filter_drops_chunks": filter_drop_chunks,
        "filter_drops_total": filter_drops_total,
        "error_chunks": error_chunks,
        "retained_phrases": retained_total,
    }
    summary_df = pd.DataFrame([summary_row])
    if summary_path.exists():
        existing = pd.read_csv(summary_path)
        existing = existing[existing["track"] != kind]  # replace same-track row
        summary_df = pd.concat([existing, summary_df], ignore_index=True)
    summary_df.to_csv(summary_path, index=False)

    # --- filter drop log ---
    drop_rows = []
    for r in results:
        for phrase, matched_word in r.dropped_by_filter:
            drop_rows.append({
                "chunk_id": r.chunk_id,
                "dropped_phrase": phrase,
                "matching_tech_word": matched_word,
            })
    pd.DataFrame(drop_rows).to_csv(
        output_folder / f"tech_filter_drops_{kind}.csv", index=False
    )

    # --- error log ---
    error_rows = [
        {"chunk_id": r.chunk_id, "track": kind, "error": r.error}
        for r in results
        if r.error is not None
    ]
    pd.DataFrame(error_rows).to_csv(
        output_folder / f"extraction_errors_{kind}.csv", index=False
    )

    print(
        f"\n[{kind}] Extraction diagnostics written to {output_folder}:\n"
        f"  total_chunks      : {total_chunks}\n"
        f"  retained_phrases  : {retained_total}\n"
        f"  sentinel_empties  : {sentinel_chunks}\n"
        f"  filter_drop_chunks: {filter_drop_chunks} ({filter_drops_total} phrases)\n"
        f"  error_chunks      : {error_chunks}"
    )


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

def filter_missing_source_text(df: pd.DataFrame, text_col: str = "text") -> pd.DataFrame:
    """Drop rows where the source text column is NaN or empty.

    Rows with missing source text are a data quality artefact (often short
    fragments that slipped through the chunk filter).  They must be removed
    before embedding or clustering to prevent a spurious "Missing source text"
    cluster from appearing in the output.

    Parameters
    ----------
    df:
        Phrases DataFrame (concerns_df or benefits_df).
    text_col:
        Name of the column holding the source paragraph text.

    Returns
    -------
    pd.DataFrame
        Filtered copy of *df* with missing-text rows removed.
    """
    mask_missing = df[text_col].isna() | (df[text_col].astype(str).str.strip() == "")
    n_missing = int(mask_missing.sum())
    if n_missing:
        print(
            f"[WARN] Dropping {n_missing} rows with missing '{text_col}' "
            "before embedding (data quality artefact)."
        )
    return df[~mask_missing].copy()


def get_embeddings_batch(texts: List[str], client, model: str = "text-embedding-3-small") -> np.ndarray:
    """Return a (len(texts), dim) array of embeddings from the OpenAI API.

    Parameters
    ----------
    texts:
        List of strings to embed.
    client:
        Initialised OpenAI client.
    model:
        Embedding model name.
    """
    response = client.embeddings.create(input=texts, model=model)
    return np.array([item.embedding for item in response.data])


# ---------------------------------------------------------------------------
# Cluster semantics
# ---------------------------------------------------------------------------

def label_cluster(
    cluster_id,
    exemplars: List[Dict[str, Any]],
    is_cross_cutting: bool,
    kind: str = "concern",
    client=None,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """Generate a label, description, and key terms for a cluster via LLM.

    Parameters
    ----------
    cluster_id:
        Cluster identifier (used as fallback label).
    exemplars:
        List of dicts; each must contain the phrase under key ``kind``
        (e.g. ``ex['concern']`` or ``ex['benefit']``) and ``'technology'``.
    is_cross_cutting:
        Whether the cluster spans multiple technologies.
    kind:
        ``'concern'`` or ``'benefit'``.
    client:
        Initialised OpenAI client.
    model:
        OpenAI model name.
    """
    if kind not in ("concern", "benefit"):
        raise ValueError(f"kind must be 'concern' or 'benefit', got {kind!r}")

    phrase_key = kind  # exemplars dict key
    exemplar_texts = "\n".join(
        f"- {ex[phrase_key]}"
        for ex in exemplars[:8]
    )
    cluster_type = (
        "cross-cutting (appears across multiple technologies)"
        if is_cross_cutting
        else "technology-specific"
    )
    prompt = (
        f"Analyze this cluster of public {kind}s from UK dialogue reports.\n\n"
        f"This cluster is {cluster_type}.\n\n"
        f"{kind.capitalize()} phrases in this cluster:\n{exemplar_texts}\n\n"
        "Provide:\n"
        f"1. SHORT LABEL (3-6 words) capturing the core {kind} theme\n"
        "2. DESCRIPTION (1-2 sentences)\n"
        "3. KEY TERMS (3-5 representative words/phrases)\n\n"
        'Return JSON only:\n{"label": "...", "description": "...", "key_terms": ["...", "..."]}'
    )
    fallback = {"label": f"Cluster {cluster_id}", "description": "", "key_terms": [], "success": False}
    if client is None:
        return fallback
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Expert qualitative researcher. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=1000,
        )
        content = response.choices[0].message.content
        if not content or not content.strip():
            return fallback
        content = content.strip()
        if "```" in content:
            for part in content.split("```"):
                if part.startswith("json"):
                    content = part[4:].strip()
                    break
                elif part.strip().startswith("{"):
                    content = part.strip()
                    break
        result = json.loads(content)
        result["success"] = True
        return result
    except Exception as exc:
        return {**fallback, "error": str(exc)}


def pretty_label(cid, cluster_labels: Optional[Dict] = None, max_len: int = 40) -> str:
    """Return a truncated human-readable label for a cluster id.

    Parameters
    ----------
    cid:
        Cluster identifier.
    cluster_labels:
        Mapping from cluster id to label string. Falls back to ``"Cluster {cid}"``
        if None or key not present.
    max_len:
        Maximum character length before truncation.
    """
    lbl = (cluster_labels or {}).get(cid, f"Cluster {cid}")
    lbl = str(lbl)
    return (lbl[: max_len - 3] + "...") if len(lbl) > max_len else lbl


def clusters_to_labels(cluster_ids, cluster_label_map: Dict) -> List[str]:
    """Map a list of cluster ids to their human-readable labels."""
    if not isinstance(cluster_ids, list):
        return []
    return [cluster_label_map.get(c, f"Cluster {c}") for c in cluster_ids]


def clusters_to_lenses(cluster_ids, cluster_to_lenses_map: Dict) -> List[str]:
    """Return sorted framing lens names for a list of cluster ids."""
    if not isinstance(cluster_ids, list):
        return []
    lenses: set = set()
    for cid in cluster_ids:
        lenses |= cluster_to_lenses_map.get(cid, set())
    return sorted(lenses)


def html_escape(s: str) -> str:
    """HTML-escape a string."""
    return _html.escape(str(s))


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def normalized_entropy(p) -> float:
    """Normalised Shannon entropy of a probability-like array, in [0, 1].

    Returns 0.0 for arrays with ≤1 non-zero element or uniform distributions
    of size 1, and 1.0 for perfectly uniform distributions.
    """
    p = np.asarray(p, dtype=float)
    p = p[p > 0]
    if len(p) <= 1:
        return 0.0
    p = p / p.sum()
    H = -(p * np.log(p)).sum()
    Hmax = np.log(len(p))
    return float(H / Hmax) if Hmax > 0 else 0.0


def hhi(p) -> float:
    """Herfindahl-Hirschman Index (sum of squared market shares), in [0, 1].

    Returns np.nan if the input sums to zero.
    """
    p = np.asarray(p, dtype=float)
    s = p.sum()
    if s <= 0:
        return float("nan")
    p = p / s
    return float((p * p).sum())


def topk_share(p, k: int = 10) -> float:
    """Share of the total held by the top-k elements.

    Returns np.nan if the input sums to zero.
    """
    p = np.asarray(p, dtype=float)
    s = p.sum()
    if s <= 0:
        return float("nan")
    p = np.sort(p)[::-1]
    return float(p[:k].sum() / s)


def parse_year(x) -> Optional[int]:
    """Parse a year integer from a string or numeric value.

    Returns None if no valid 4-digit year in 1900–2100 can be found.
    """
    s = str(x).strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) >= 4:
        y = int(digits[:4])
        if 1900 <= y <= 2100:
            return y
    return None


def tokenize(s: str) -> List[str]:
    """Lowercase, strip punctuation, and return tokens of length > 3."""
    s = str(s).lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return [w for w in s.split() if len(w) > 3]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def is_privacy_text(s: str) -> bool:
    """Return True if *s* contains any PRIVACY_TERMS keyword."""
    return bool(_PRIVACY_PATTERN.search(str(s)))


def entropy_by_year(g: pd.DataFrame, cluster_col: str = "cluster_id") -> float:
    """Normalised entropy of cluster distribution within a year-group.

    Intended for use with ``groupby(...).apply(entropy_by_year)``.
    """
    p = g[cluster_col].value_counts(normalize=True).values
    return normalized_entropy(p)


def ai_fingerprint_over_crosscut(
    sal: pd.DataFrame,
    cross_mask,
    ai_col: str,
) -> pd.Series:
    """AI salience advantage over the non-AI mean for cross-cutting clusters.

    Parameters
    ----------
    sal:
        clusters × technologies salience DataFrame.
    cross_mask:
        Boolean Series/array selecting cross-cutting clusters (index = cluster ids).
    ai_col:
        Column name for the AI technology.

    Returns
    -------
    pd.Series of (AI share − mean non-AI share) sorted descending.
    """
    sub = sal.loc[cross_mask]
    row_total = sub.sum(axis=1).replace(0, float("nan"))
    shares = sub.div(row_total, axis=0).fillna(0)
    ai_share = shares[ai_col]
    other_cols = [c for c in shares.columns if c != ai_col]
    other_mean = shares[other_cols].mean(axis=1) if other_cols else pd.Series(0, index=shares.index)
    return (ai_share - other_mean).sort_values(ascending=False)


# ---------------------------------------------------------------------------
# Sensitivity analysis — CIP-0002
# ---------------------------------------------------------------------------

def run_sensitivity(
    k: int,
    kind: str,
    embeddings_normalized: np.ndarray,
    df: pd.DataFrame,
    output_folder: Path,
    random_seed: int = 42,
    tech_col: str = "technology_meta",
    phrase_col: Optional[str] = None,
    framing_lens_mappings: Optional[Dict] = None,
    baseline_k: int = 75,
) -> None:
    """Run sensitivity analysis for a single cluster count *k*.

    Replaces the notebook's duplicate ``run_for_k`` definitions (cells 104 and
    114). Output filenames are prefixed with ``{kind}_sensitivity_`` so concern
    and benefit runs never overwrite each other.

    Parameters
    ----------
    k:
        Number of clusters for this sensitivity run.
    kind:
        ``'concern'`` or ``'benefit'``.
    embeddings_normalized:
        L2-normalised embedding matrix (n_phrases × dim).
    df:
        ``concerns_df`` or ``benefits_df``; must contain *tech_col* and
        ``'cluster_id'`` columns.
    output_folder:
        Directory where output files are written.
    random_seed:
        KMeans random state.
    tech_col:
        Column name for technology labels.
    phrase_col:
        Column name for phrase text (defaults to *kind*).
    framing_lens_mappings:
        Optional dict of lens name → {'cluster_ids': [...]} for lens analysis.
    baseline_k:
        Cluster count of the headline run (used for stable-core comparison).
    """
    try:
        from sklearn.cluster import KMeans  # type: ignore
        import matplotlib.pyplot as plt  # type: ignore
    except ImportError as exc:
        raise ImportError("scikit-learn and matplotlib are required for sensitivity analysis.") from exc

    if kind not in ("concern", "benefit"):
        raise ValueError(f"kind must be 'concern' or 'benefit', got {kind!r}")

    if phrase_col is None:
        phrase_col = kind

    output_folder = Path(output_folder)
    prefix = f"{kind}_sensitivity"

    # ── Re-cluster ─────────────────────────────────────────────────────────
    km = KMeans(n_clusters=k, random_state=random_seed, n_init="auto")
    labels = km.fit_predict(embeddings_normalized)

    run_df = df.copy()
    run_df["cluster_id_k"] = labels

    # ── Stable core: entropy × prevalence ──────────────────────────────────
    global_prev = run_df["cluster_id_k"].value_counts(normalize=True)
    ent = {}
    for cid in range(k):
        mask = run_df["cluster_id_k"] == cid
        tech_counts = run_df.loc[mask, tech_col].value_counts()
        probs = tech_counts.values if tech_counts.sum() > 0 else np.array([])
        ent[cid] = normalized_entropy(probs)

    stable_df = pd.DataFrame({
        "cluster_id_k": list(range(k)),
        "tech_entropy": [ent[i] for i in range(k)],
        "global_prevalence": [float(global_prev.get(i, 0)) for i in range(k)],
    }).sort_values(["global_prevalence", "tech_entropy"], ascending=False)

    plt.figure(figsize=(7, 5))
    plt.scatter(stable_df["tech_entropy"], stable_df["global_prevalence"])
    plt.xlabel("Entropy across technologies")
    plt.ylabel(f"Share of all extracted {kind}s")
    plt.title(f"Stable core structure (k={k}, {kind}s)")
    plt.tight_layout()
    plt.savefig(output_folder / f"{prefix}_stable_core_k{k}.png")
    plt.close()

    stable_df.to_csv(output_folder / f"{prefix}_stable_core_k{k}.csv", index=False)

    # ── AI fingerprint ──────────────────────────────────────────────────────
    techs = sorted(run_df[tech_col].dropna().unique().tolist())
    non_ai = [t for t in techs if str(t).strip().lower() not in ("ai", "artificial intelligence")]

    prof: Dict[str, Dict] = {}
    for t in techs:
        m = run_df[tech_col] == t
        total = int(m.sum())
        if total == 0:
            continue
        counts = run_df.loc[m, "cluster_id_k"].value_counts()
        prof[t] = (counts / total).to_dict()

    prof_df = pd.DataFrame(prof).T.fillna(0)
    ai_candidates = [c for c in prof_df.index if str(c).strip().lower() in ("ai", "artificial intelligence")]

    if ai_candidates and non_ai:
        ai_row = ai_candidates[0]
        non_ai_avg = prof_df.loc[[t for t in non_ai if t in prof_df.index]].mean(axis=0)
        diff = (prof_df.loc[ai_row] - non_ai_avg).sort_values()
        top_low = diff.head(5).index.tolist()
        top_high = diff.tail(7).index.tolist()
        sel = top_low + top_high

        fingerprint_df = pd.DataFrame({
            "cluster_id": sel,
            f"ai_{kind}_share": [prof_df.loc[ai_row, c] for c in sel],
            f"non_ai_{kind}_share": [float(non_ai_avg.get(c, 0)) for c in sel],
            "ai_advantage": [float(diff[c]) for c in sel],
        })
        fingerprint_df.to_csv(output_folder / f"{prefix}_fingerprint_k{k}.csv", index=False)

        # Simple HTML fingerprint
        html_content = (
            f"<h2>AI {kind.capitalize()} Fingerprint (k={k})</h2>\n"
            + fingerprint_df.to_html(index=False)
        )
        (output_folder / f"{prefix}_fingerprint_k{k}.html").write_text(html_content)

    # ── Time metrics ────────────────────────────────────────────────────────
    time_df = run_df.copy()
    time_df["__year__"] = time_df.get("year", pd.Series(dtype=object)).apply(parse_year)
    time_df = time_df.dropna(subset=["__year__"])
    time_df["__year__"] = time_df["__year__"].astype(int)

    ai_mask = time_df[tech_col].astype(str).str.strip().str.lower().isin(("ai", "artificial intelligence"))
    ai_time = time_df[ai_mask]

    if not ai_time.empty:
        entropy_ts = (
            ai_time.groupby("__year__")["cluster_id_k"]
            .apply(lambda g: normalized_entropy(g.value_counts().values))
            .rename("entropy")
            .reset_index()
            .rename(columns={"__year__": "year"})
        )
        entropy_ts.to_csv(output_folder / f"{prefix}_time_metrics_k{k}.csv", index=False)

        plt.figure(figsize=(8, 4))
        plt.plot(entropy_ts["year"], entropy_ts["entropy"], marker="o")
        plt.xlabel("Year")
        plt.ylabel(f"Normalised entropy of AI {kind} distribution")
        plt.title(f"AI {kind.capitalize()} Diversity Over Time (k={k})")
        plt.tight_layout()
        plt.savefig(output_folder / f"{prefix}_entropy_k{k}.png")
        plt.close()

    # ── Lens salience (optional) ────────────────────────────────────────────
    if framing_lens_mappings:
        lens_rows = []
        for lens_name, data in framing_lens_mappings.items():
            lens_cluster_ids = set(data.get("cluster_ids", []))
            for t in techs:
                t_mask = run_df[tech_col] == t
                t_df = run_df[t_mask]
                if t_df.empty:
                    continue
                lens_count = t_df["cluster_id_k"].isin(lens_cluster_ids).sum()
                lens_rows.append({
                    "technology": t,
                    "lens": lens_name,
                    f"{kind}_phrases_in_lens": int(lens_count),
                    f"share_of_{kind}s": lens_count / len(t_df),
                })
        if lens_rows:
            lens_df = pd.DataFrame(lens_rows)
            lens_df.to_csv(output_folder / f"{prefix}_lens_k{k}.csv", index=False)

            html_content = f"<h2>{kind.capitalize()} Lens Salience (k={k})</h2>\n" + lens_df.to_html(index=False)
            (output_folder / f"{prefix}_radar_k{k}.html").write_text(html_content)


# ---------------------------------------------------------------------------
# Vocabulary frequency diagnostic — CIP-0004
# ---------------------------------------------------------------------------

def vocabulary_frequency_diagnostic(
    phrases: List[str],
    kind: str,
    output_folder: Path,
    meta_vocabulary: Optional[List[str]] = None,
    top_n: int = 100,
) -> pd.DataFrame:
    """Compute unigram and bigram frequency for extracted phrases and flag meta-vocabulary.

    Writes ``{kind}_vocab_frequency.csv`` to *output_folder* containing the
    top-*top_n* terms ranked by frequency.  Terms that appear in
    *meta_vocabulary* (or :data:`META_VOCABULARY` by default) are marked with
    ``is_meta_vocab=True``.

    Parameters
    ----------
    phrases:
        List of extracted phrase strings (e.g. ``concerns_df["concern"].tolist()``).
    kind:
        ``"concern"`` or ``"benefit"`` — used in the output filename.
    output_folder:
        Directory where the CSV is written.
    meta_vocabulary:
        Override the default :data:`META_VOCABULARY` list.
    top_n:
        How many top terms to include in the CSV.

    Returns
    -------
    pd.DataFrame
        The frequency table (also written to disk).
    """
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    if meta_vocabulary is None:
        meta_vocabulary = META_VOCABULARY

    meta_set = {m.lower() for m in meta_vocabulary}

    token_pattern = re.compile(r"\b[a-z]{3,}\b")

    counts: Counter = Counter()
    for phrase in phrases:
        tokens = token_pattern.findall(phrase.lower())
        counts.update(tokens)
        # bigrams
        for a, b in zip(tokens, tokens[1:]):
            counts.update([f"{a} {b}"])

    total_phrases = max(len(phrases), 1)
    rows = []
    for term, count in counts.most_common(top_n):
        rows.append(
            {
                "term": term,
                "count": count,
                "pct_of_phrases": round(100 * count / total_phrases, 2),
                "is_meta_vocab": term in meta_set,
            }
        )

    _cols = ["term", "count", "pct_of_phrases", "is_meta_vocab"]
    df = pd.DataFrame(rows, columns=_cols) if rows else pd.DataFrame(columns=_cols)
    out_path = output_folder / f"{kind}_vocab_frequency.csv"
    df.to_csv(out_path, index=False)

    # --- console report ---
    flagged = df[df["is_meta_vocab"]]
    print(f"\n[{kind}] Vocabulary frequency diagnostic — top {top_n} terms written to {out_path}")
    print(f"  Total phrases analysed : {total_phrases}")
    if flagged.empty:
        print("  No meta-vocabulary terms in top terms.")
    else:
        print(f"  Meta-vocabulary terms found ({len(flagged)}):")
        for _, row in flagged.iterrows():
            print(f"    '{row['term']}': {row['count']} occurrences ({row['pct_of_phrases']}% of phrases)")

    return df


# ---------------------------------------------------------------------------
# Validation summary — CIP-0005
# ---------------------------------------------------------------------------

def generate_validation_summary(
    output_folder: Path,
    n_concern_clusters: Optional[int] = None,
    n_benefit_clusters: Optional[int] = None,
) -> Path:
    """Write a plain-text validation summary for Activity 4 of the playbook.

    Reads the diagnostic CSVs produced by earlier pipeline stages and writes
    ``validation_summary.txt`` to *output_folder*.  This file is intended to
    be included in the export pack so reviewers can quickly verify counts.

    Parameters
    ----------
    output_folder:
        Directory containing pipeline output CSVs.
    n_concern_clusters:
        Expected number of concern clusters (``N_CONCERN_CLUSTERS``).
    n_benefit_clusters:
        Expected number of benefit clusters (``N_BENEFIT_CLUSTERS``).

    Returns
    -------
    Path
        Path to the written ``validation_summary.txt``.
    """
    output_folder = Path(output_folder)
    lines: List[str] = [
        "Public Dialogue Analyser — Validation Summary",
        "=" * 48,
        "",
    ]

    def _count(csv_name: str) -> int:
        p = output_folder / csv_name
        if not p.exists():
            return -1
        try:
            return len(pd.read_csv(p))
        except Exception:
            return -1

    def _yield_row(kind: str) -> Optional[dict]:
        p = output_folder / "extraction_yield_summary.csv"
        if not p.exists():
            return None
        try:
            df = pd.read_csv(p)
            row = df[df["track"] == kind]
            return row.iloc[0].to_dict() if not row.empty else None
        except Exception:
            return None

    # --- Paragraph chunks ---
    n_chunks = _count("paragraph_chunks.csv")
    lines += [
        f"Paragraphs (chunks): {n_chunks if n_chunks >= 0 else 'FILE NOT FOUND'}",
        "",
    ]

    # --- Concerns ---
    concern_yield = _yield_row("concern")
    n_concern_phrases = _count("extracted_concerns.csv")
    lines.append("CONCERNS")
    lines.append("-" * 24)
    if concern_yield:
        lines += [
            f"  Total chunks processed : {int(concern_yield['total_chunks'])}",
            f"  Retained phrases       : {int(concern_yield['retained_phrases'])}",
            f"  Sentinel (no concern)  : {int(concern_yield['sentinel_empties'])}",
            f"  Filter drops (chunks)  : {int(concern_yield['filter_drops_chunks'])} "
            f"({int(concern_yield['filter_drops_total'])} phrases)",
            f"  API errors             : {int(concern_yield['error_chunks'])}",
        ]
    lines.append(
        f"  extracted_concerns.csv : {n_concern_phrases if n_concern_phrases >= 0 else 'FILE NOT FOUND'} rows"
    )
    if n_concern_clusters is not None:
        n_actual = _count("cluster_summary.csv")
        match = "OK" if n_actual == n_concern_clusters else f"MISMATCH (expected {n_concern_clusters})"
        lines.append(f"  Concern clusters       : {n_actual} [{match}]")
    lines.append("")

    # --- Benefits ---
    benefit_yield = _yield_row("benefit")
    n_benefit_phrases = _count("extracted_benefits.csv")
    lines.append("BENEFITS")
    lines.append("-" * 24)
    if benefit_yield:
        lines += [
            f"  Total chunks processed : {int(benefit_yield['total_chunks'])}",
            f"  Retained phrases       : {int(benefit_yield['retained_phrases'])}",
            f"  Sentinel (no benefit)  : {int(benefit_yield['sentinel_empties'])}",
            f"  Filter drops (chunks)  : {int(benefit_yield['filter_drops_chunks'])} "
            f"({int(benefit_yield['filter_drops_total'])} phrases)",
            f"  API errors             : {int(benefit_yield['error_chunks'])}",
        ]
    lines.append(
        f"  extracted_benefits.csv : {n_benefit_phrases if n_benefit_phrases >= 0 else 'FILE NOT FOUND'} rows"
    )
    lines.append("")

    # --- File checklist ---
    lines += ["FILE CHECKLIST", "-" * 24]
    expected_files = [
        "paragraph_chunks.csv",
        "extracted_concerns.csv",
        "extracted_benefits.csv",
        "cluster_summary.csv",
        "cluster_exemplars.json",
        "cluster_labels.json",
        "traceability_paragraphs.csv",
        "evidence_pack_paragraphs.html",
        "extraction_yield_summary.csv",
    ]
    for fname in expected_files:
        present = (output_folder / fname).exists()
        lines.append(f"  {'[OK]' if present else '[MISSING]':10s} {fname}")

    lines += ["", "Generated by dialogue_utils.generate_validation_summary()"]

    out_path = output_folder / "validation_summary.txt"
    out_path.write_text("\n".join(lines))
    print(f"Validation summary written to {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def _volume_table(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Phrase counts and paragraph incidence by technology × year.

    Parameters
    ----------
    df:
        concerns_df or benefits_df; must contain 'technology', 'year', and a
        paragraph-id column (paragraph_id, para_id, or chunk_id).
    kind:
        ``'concern'`` or ``'benefit'`` — used to name output columns.
    """
    cols = df.columns
    pid = next(
        (c for c in ("paragraph_id", "para_id", "chunk_id") if c in cols),
        None,
    )
    if pid is None:
        raise ValueError("Expected a paragraph id column (paragraph_id, para_id, or chunk_id).")
    phrase_counts = df.groupby(["technology", "year"]).size().rename(f"{kind}_phrases")
    para_inc = (
        df.groupby(["technology", "year"])[pid]
        .nunique()
        .rename(f"{kind}_paragraphs_with_ge1")
    )
    return pd.concat([phrase_counts, para_inc], axis=1)


def _top_clusters(
    df: pd.DataFrame,
    summary_df: Optional[pd.DataFrame],
    kind: str,
    n: int = 10,
) -> pd.DataFrame:
    """Return the top-n clusters by phrase count with optional labels.

    Parameters
    ----------
    df:
        concerns_df or benefits_df; must contain 'cluster_id'.
    summary_df:
        Optional dataframe with 'cluster_id' and 'label' columns.
    kind:
        ``'concern'`` or ``'benefit'`` — inserted as a 'kind' column.
    n:
        Number of top clusters to return.
    """
    counts = (
        df["cluster_id"]
        .value_counts()
        .head(n)
        .rename("count")
        .reset_index()
        .rename(columns={"index": "cluster_id"})
    )
    if summary_df is not None and {"cluster_id", "label"}.issubset(summary_df.columns):
        counts = counts.merge(summary_df[["cluster_id", "label"]], on="cluster_id", how="left")
    counts.insert(0, "kind", kind)
    return counts
