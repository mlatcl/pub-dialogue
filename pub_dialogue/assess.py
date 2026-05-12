"""
pub_dialogue.assess — Question-agnostic data assessment stage.

This module owns everything that characterises the corpus *without* any reference to
the research question.  Functions here can be run by any researcher regardless of what
they are looking for, making the outputs independently reusable.

A function belongs here if and only if it can be completed without knowing the research
question — i.e. without invoking any LLM extraction prompt, without filtering by
technology-term lists, and without inspecting extracted phrases.

Public API:
  Data quality plots:
    plot_data_quality
  Chunk content quality:
    flag_chunk_quality
  Extraction diagnostics (question-agnostic quality checks):
    validate_extraction_cache
    write_extraction_diagnostics
    filter_missing_source_text
  Vocabulary diagnostics:
    vocabulary_frequency_diagnostic
  Privacy-term detection:
    is_privacy_text
  Temporal diversity:
    entropy_by_year
  Validation summary:
    generate_validation_summary

Constants:
  META_VOCABULARY     — meta-vocabulary stop-list
  PRIVACY_TERMS       — keywords for privacy-cluster detection
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

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
# Extraction-cache validation (question-agnostic quality check)
# ---------------------------------------------------------------------------

def validate_extraction_cache(
    cache: Dict[str, Any],
    kind: str,
    warn_threshold: float = 0.30,
) -> bool:
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
    results: list,
    kind: str,
    output_folder: Path,
) -> None:
    """Write yield-diagnostic files after an extraction pass.

    Produces three files in *output_folder*:

    * ``extraction_yield_summary.csv`` — one row per (kind, run) with counts
      of sentinels, filter drops, errors, and retained phrases.
    * ``tech_filter_drops_{kind}.csv`` — one row per dropped phrase with the
      matching tech-word substring.
    * ``extraction_errors_{kind}.csv`` — one row per chunk that raised an
      exception during the API call.

    Parameters
    ----------
    results:
        List of :class:`~pub_dialogue.address.ExtractionResult` objects.
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
        existing = existing[existing["track"] != kind]
        summary_df = pd.concat([existing, summary_df], ignore_index=True)
    summary_df.to_csv(summary_path, index=False)

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
# Temporal diversity metric
# ---------------------------------------------------------------------------

def entropy_by_year(g: pd.DataFrame, cluster_col: str = "cluster_id") -> float:
    """Normalised entropy of cluster distribution within a year-group.

    Intended for use with ``groupby(...).apply(entropy_by_year)``.
    """
    from pub_dialogue.utils import normalized_entropy  # avoid circular import
    p = g[cluster_col].value_counts(normalize=True).values
    return normalized_entropy(p)


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


# ---------------------------------------------------------------------------
# Validation summary
# ---------------------------------------------------------------------------

def generate_validation_summary(
    output_folder: Path,
    n_concern_clusters: Optional[int] = None,
    n_benefit_clusters: Optional[int] = None,
) -> Path:
    """Write a plain-text validation summary for Activity 4 of the playbook.

    Reads the diagnostic CSVs produced by earlier pipeline stages and writes
    ``validation_summary.txt`` to *output_folder*.

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

    n_chunks = _count("paragraph_chunks.csv")
    lines += [
        f"Paragraphs (chunks): {n_chunks if n_chunks >= 0 else 'FILE NOT FOUND'}",
        "",
    ]

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

    lines += ["", "Generated by pub_dialogue.assess.generate_validation_summary()"]

    out_path = output_folder / "validation_summary.txt"
    out_path.write_text("\n".join(lines))
    print(f"Validation summary written to {out_path}")
    return out_path
