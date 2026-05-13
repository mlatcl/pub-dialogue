"""
pub_dialogue.assess — Question-agnostic data assessment stage.

This module owns everything that characterises the corpus *without* any reference to
the research question.  Functions here can be run by any researcher regardless of what
they are looking for, making the outputs independently reusable.

A function belongs here if and only if it can be completed without knowing the research
question — i.e. without invoking any LLM extraction prompt, without filtering by
technology-term lists, and without inspecting extracted phrases.

Public API:
  Stage class (CIP-0010):
    AssessStage — typed config dataclass with assess-phase helper methods:
      validate_cache, plot_quality, validation_summary
  Data quality plots:
    plot_data_quality
  Chunk content quality:
    flag_chunk_quality
  Extraction pre-filter:
    filter_missing_source_text
  Vocabulary diagnostics:
    vocabulary_frequency_diagnostic
  Privacy-term detection:
    is_privacy_text

Constants:
  META_VOCABULARY     — meta-vocabulary stop-list
  PRIVACY_TERMS       — keywords for privacy-cluster detection
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pub_dialogue.access import AccessStage

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# AssessStage — typed config dataclass (CIP-0010 Phase 1)
# ---------------------------------------------------------------------------

@dataclass
class AssessStage:
    """Configuration and entry-point for the Assess pipeline stage.

    Holds a reference to the AccessStage so assess-phase helpers can read
    folder paths without repeating them.  All existing module-level functions
    remain unchanged.

    Usage in notebook setup cells::

        from pub_dialogue.access import AccessStage
        from pub_dialogue.assess import AssessStage
        access = AccessStage()
        assess = AssessStage(access=access)
    """

    access: "AccessStage"

    # -------------------------------------------------------------------
    # Assess-phase helpers (CIP-0010 Phase 4)
    # -------------------------------------------------------------------

    def validate_cache(
        self,
        cache: "Dict[str, Any]",
        kind: str,
        warn_threshold: float = 0.3,
    ) -> bool:
        """Check a loaded extraction cache for signs of a partial-failure run.

        Thin wrapper around :func:`pub_dialogue.address.validate_extraction_cache`.

        Parameters
        ----------
        cache:          Mapping of ``chunk_id → list[phrase]`` as loaded from JSON.
        kind:           ``'concern'`` or ``'benefit'``
        warn_threshold: Fraction of empty entries above which ``False`` is returned.
        """
        from pub_dialogue.address import validate_extraction_cache
        return validate_extraction_cache(cache, kind=kind, warn_threshold=warn_threshold)

    def plot_quality(
        self,
        chunks_df: "pd.DataFrame",
        filename: str = "data_quality_overview.png",
        dpi: int = 150,
    ) -> Path:
        """Produce a 2×2 data-quality summary figure and write it to disk.

        Thin wrapper around :func:`plot_data_quality` that uses
        ``self.access.output_folder`` as the destination.

        Parameters
        ----------
        chunks_df: DataFrame of corpus chunks (must have ``technology``, ``year``,
                   ``word_count``, ``char_count`` columns).
        filename:  Output filename (default ``data_quality_overview.png``).
        dpi:       Figure resolution in dots per inch.

        Returns
        -------
        Path of the written figure file.
        """
        return plot_data_quality(
            chunks_df,
            output_folder=self.access.output_folder,
            filename=filename,
            dpi=dpi,
        )

    def validation_summary(
        self,
        n_concern_clusters: Optional[int] = None,
        n_benefit_clusters: Optional[int] = None,
    ) -> Path:
        """Write a plain-text validation summary for Activity 4 of the playbook.

        Thin wrapper around :func:`pub_dialogue.address.generate_validation_summary`
        that uses ``self.access.output_folder`` as the destination.

        Parameters
        ----------
        n_concern_clusters: Total number of concern clusters (optional, for summary).
        n_benefit_clusters: Total number of benefit clusters (optional, for summary).

        Returns
        -------
        Path of the written ``validation_summary.txt`` file.
        """
        from pub_dialogue.address import generate_validation_summary
        return generate_validation_summary(
            self.access.output_folder,
            n_concern_clusters=n_concern_clusters,
            n_benefit_clusters=n_benefit_clusters,
        )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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

# Patterns for chunk content-quality heuristics
_BIB_PATTERN = re.compile(
    r"\b(et al\.?|doi:|http(s)?://|pp?\.\s*\d+|vol\.|isbn|issn)\b",
    re.IGNORECASE,
)
_TABLE_PATTERN = re.compile(r"%")
_CITATION_YEAR = re.compile(r"\([12][0-9]{3}\)")


# ---------------------------------------------------------------------------
# Data quality plots
# ---------------------------------------------------------------------------

def plot_data_quality(
    chunks_df: pd.DataFrame,
    output_folder: Path,
    filename: str = "data_quality_overview.png",
    dpi: int = 150,
) -> Path:
    """Produce a 2×2 summary figure of paragraph-level data quality.

    Creates four subplots:

    * **Top-left**: paragraph count by technology (horizontal bar).
    * **Top-right**: paragraph count by year (vertical bar).
    * **Bottom-left**: word-count distribution (histogram).
    * **Bottom-right**: paragraph count per document (vertical bar).

    Saves the figure to *output_folder* / *filename* and returns the path.

    Parameters
    ----------
    chunks_df:
        DataFrame with at least ``technology_meta``, ``year``,
        ``word_count``, and ``source_file`` columns.
    output_folder:
        Directory where the PNG is written (created if absent).
    filename:
        Output file name.
    dpi:
        Figure resolution.

    Returns
    -------
    Path
        Path to the saved PNG.
    """
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except ImportError as exc:
        raise ImportError("matplotlib is required for plot_data_quality.") from exc

    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    tech_counts = chunks_df["technology_meta"].value_counts()
    axes[0, 0].barh(tech_counts.index, tech_counts.values, color="steelblue")
    axes[0, 0].set_xlabel("Number of Paragraphs")
    axes[0, 0].set_title("Paragraphs by Technology")
    axes[0, 0].invert_yaxis()

    year_counts = chunks_df.groupby("year").size()
    axes[0, 1].bar(year_counts.index.astype(str), year_counts.values, color="steelblue")
    axes[0, 1].set_xlabel("Year")
    axes[0, 1].set_ylabel("Paragraphs")
    axes[0, 1].set_title("Paragraphs by Year")
    axes[0, 1].tick_params(axis="x", rotation=45)

    axes[1, 0].hist(chunks_df["word_count"], bins=30, color="steelblue", edgecolor="white")
    axes[1, 0].set_xlabel("Word Count")
    axes[1, 0].set_ylabel("Frequency")
    axes[1, 0].set_title("Paragraph Length Distribution")

    doc_chunks = chunks_df.groupby("source_file").size().sort_values(ascending=False)
    axes[1, 1].bar(range(len(doc_chunks)), doc_chunks.values, color="steelblue")
    axes[1, 1].set_xlabel("Document Index")
    axes[1, 1].set_ylabel("Paragraphs")
    axes[1, 1].set_title("Paragraphs per Document")

    plt.tight_layout()
    out_path = output_folder / filename
    plt.savefig(out_path, dpi=dpi)

    return out_path


# ---------------------------------------------------------------------------
# Chunk content-quality heuristics
# ---------------------------------------------------------------------------

def _looks_like_bibliography(text: str) -> bool:
    """Return True if *text* matches bibliography-fragment heuristics."""
    if not isinstance(text, str):
        return False
    return bool(_BIB_PATTERN.search(text)) and bool(_CITATION_YEAR.search(text))


def _looks_like_table_row(text: str) -> bool:
    """Return True if *text* contains ≥ 2 percent signs (survey-table heuristic)."""
    if not isinstance(text, str):
        return False
    return len(_TABLE_PATTERN.findall(text)) >= 2


def flag_chunk_quality(
    chunks_df: pd.DataFrame,
    output_folder: Path,
    min_chunk_words: int = 40,
    min_chunk_chars: int = 80,
    filename: str = "chunk_quality_flagged.csv",
) -> pd.DataFrame:
    """Add content-quality flags to *chunks_df* and write flagged rows to CSV.

    Applies two heuristic filters:

    * ``likely_bibliography``: matches ``et al.``, ``doi:``, ``http…``,
      ``pp. N``, ``vol.``, ``isbn``, ``issn`` *and* a ``(YYYY)`` citation.
    * ``likely_table_row``: two or more ``%`` characters in the chunk text.

    These are diagnostics only — the function never drops rows.  The flagged
    subset is written to *output_folder* / *filename* for manual inspection.

    Parameters
    ----------
    chunks_df:
        DataFrame with at least ``chunk_id``, ``source_file``, ``word_count``,
        and ``text`` columns.  Modified in-place to add the flag columns.
    output_folder:
        Directory where the flagged CSV is written.
    min_chunk_words, min_chunk_chars:
        Passed through to the console message for reference only.
    filename:
        Output CSV file name.

    Returns
    -------
    pd.DataFrame
        The input *chunks_df* with ``likely_bibliography`` and
        ``likely_table_row`` columns added.
    """
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    chunks_df = chunks_df.copy()
    chunks_df["likely_bibliography"] = chunks_df["text"].apply(_looks_like_bibliography)
    chunks_df["likely_table_row"] = chunks_df["text"].apply(_looks_like_table_row)

    n_total = len(chunks_df)
    n_bib = int(chunks_df["likely_bibliography"].sum())
    n_table = int(chunks_df["likely_table_row"].sum())

    print(f"Chunk content quality (n = {n_total}):")
    print(f"  Likely bibliography fragment: {n_bib}  ({n_bib/n_total*100:.1f}%)")
    print(f"  Likely survey-table row:      {n_table}  ({n_table/n_total*100:.1f}%)")
    print()
    print("These chunks are kept for analysis (the diagnostic does not filter).")
    print("If the contamination rate is high, consider raising MIN_CHUNK_WORDS.")
    print(f"Current floor: {min_chunk_words} words / {min_chunk_chars} chars.")

    flagged = chunks_df[
        chunks_df["likely_bibliography"] | chunks_df["likely_table_row"]
    ][["chunk_id", "source_file", "word_count", "likely_bibliography", "likely_table_row", "text"]]
    flagged.to_csv(output_folder / filename, index=False)

    return chunks_df


# ---------------------------------------------------------------------------
# Embedding pre-filter
# ---------------------------------------------------------------------------

def filter_missing_source_text(
    df: pd.DataFrame,
    text_col: str = "text",
) -> pd.DataFrame:
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


# ---------------------------------------------------------------------------
# Privacy-term detection
# ---------------------------------------------------------------------------

def is_privacy_text(s: str) -> bool:
    """Return True if *s* contains any PRIVACY_TERMS keyword."""
    return bool(_PRIVACY_PATTERN.search(str(s)))


# ---------------------------------------------------------------------------
# Vocabulary frequency diagnostic
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
        List of extracted phrase strings.
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
        for a, b in zip(tokens, tokens[1:]):
            counts.update([f"{a} {b}"])

    total_phrases = max(len(phrases), 1)
    rows = []
    for term, count in counts.most_common(top_n):
        rows.append({
            "term": term,
            "count": count,
            "pct_of_phrases": round(100 * count / total_phrases, 2),
            "is_meta_vocab": term in meta_set,
        })

    _cols = ["term", "count", "pct_of_phrases", "is_meta_vocab"]
    df = pd.DataFrame(rows, columns=_cols) if rows else pd.DataFrame(columns=_cols)
    out_path = output_folder / f"{kind}_vocab_frequency.csv"
    df.to_csv(out_path, index=False)

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


