"""
pub_dialogue.utils — Shared utilities and backward-compatibility re-exports.

This module provides two things:

1. **Shared helpers** that do not belong exclusively to any single pipeline
   stage: display utilities, pure mathematical functions, cluster-label
   formatting, and general text helpers.

2. **Re-exports** of every public name from the three pipeline-stage modules
   (:mod:`pub_dialogue.access`, :mod:`pub_dialogue.assess`,
   :mod:`pub_dialogue.address`) so that existing code that imports from
   ``pub_dialogue.utils`` continues to work without modification.

Import convention in notebooks::

    import pub_dialogue.utils as du

All names can still be imported as before::

    from pub_dialogue.utils import (
        extract_chunks_from_pdf, load_artifacts, extract_phrases, ...
    )
"""

from __future__ import annotations

import html as _html
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Re-exports from pub_dialogue.access
# ---------------------------------------------------------------------------

from pub_dialogue.access import (  # noqa: F401
    MIN_CHUNK_WORDS,
    MIN_CHUNK_CHARS,
    MAX_CHUNK_WORDS,
    SENTENCE_FALLBACK_TARGET_WORDS,
    SENTENCE_FALLBACK_MIN_PARAGRAPHS,
    _chunk_stats,
    reset_chunk_stats,
    get_chunk_stats,
    _split_into_sentences,
    _repack_sentences_into_chunks,
    _extract_paragraphs_from_blocks,
    _paragraph_split,
    extract_chunks_from_pdf,
    load_artifacts,
    save_checkpoint,
    load_checkpoint,
)

# ---------------------------------------------------------------------------
# Re-exports from pub_dialogue.assess
# ---------------------------------------------------------------------------

from pub_dialogue.assess import (  # noqa: F401
    META_VOCABULARY,
    PRIVACY_TERMS,
    _PRIVACY_PATTERN,
    is_privacy_text,
    filter_missing_source_text,
    vocabulary_frequency_diagnostic,
)

from pub_dialogue.address import (  # noqa: F401 — moved from assess (address-stage outputs)
    entropy_by_year,
    validate_extraction_cache,
    write_extraction_diagnostics,
    generate_validation_summary,
)

# ---------------------------------------------------------------------------
# Re-exports from pub_dialogue.address
# ---------------------------------------------------------------------------

from pub_dialogue.address import (  # noqa: F401
    CROSSCUTTING_ENTROPY_THRESHOLD,
    EXTRACTION_PROMPT,
    BENEFIT_EXTRACTION_PROMPT,
    DEFAULT_TECH_WORDS,
    _SENTINELS,
    ExtractionResult,
    configure_rate_limiter,
    extract_phrases,
    get_embeddings_batch,
    label_cluster,
    ai_fingerprint_over_crosscut,
    run_sensitivity,
    _volume_table,
    _top_clusters,
    EXTRACTION_PROMPT_B,
    EXTRACTION_PROMPT_C,
    BENEFIT_EXTRACTION_PROMPT_B,
    BENEFIT_EXTRACTION_PROMPT_C,
    CONCERN_PROMPT_VARIANTS,
    BENEFIT_PROMPT_VARIANTS,
    run_prompt_sensitivity,
)

# ---------------------------------------------------------------------------
# Safe CSV reader
# ---------------------------------------------------------------------------

def read_csv_safe(path, **kwargs) -> "pd.DataFrame":
    """Read a CSV that may be empty or missing without raising EmptyDataError.

    Returns an empty DataFrame (with no columns) when the file does not exist,
    has zero bytes, or contains only whitespace — the three cases that cause
    ``pd.read_csv`` to raise ``EmptyDataError``.
    """
    from pathlib import Path
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(p, **kwargs)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Display helpers (stay in utils — used by all three stages)
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


# ---------------------------------------------------------------------------
# Pure mathematical utilities (stay in utils — referenced by assess & address)
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
# Cluster-label formatting (stay in utils — used by address and notebooks)
# ---------------------------------------------------------------------------

def pretty_label(cid, cluster_labels: Optional[Dict] = None, max_len: int = 40) -> str:
    """Return a truncated human-readable label for a cluster id.

    Parameters
    ----------
    cid:
        Cluster identifier.
    cluster_labels:
        Mapping from cluster id to label string.
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
