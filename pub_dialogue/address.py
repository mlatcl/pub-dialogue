"""
pub_dialogue.address — Research-question-specific analysis stage.

This module owns everything that requires knowledge of the research question: LLM-based
phrase extraction, embedding generation, clustering, labelling, and downstream analysis.
All functions here operate on the outputs of the access and assess stages.

Public API:
  Stage class (CIP-0010):
    AddressStage — typed config dataclass centralising all analysis constants
  Extraction:
    ExtractionResult (dataclass)
    extract_phrases
  Embeddings:
    get_embeddings_batch
  Cluster labelling:
    label_cluster, label_benefit_cluster
  Analysis metrics:
    ai_fingerprint_over_crosscut
  Sensitivity analysis:
    run_sensitivity
  Temporal helpers:
    assign_window, _parse_listcol
  Comparison helpers:
    _volume_table, _top_clusters
  Export helpers:
    _clean_for_xlsx
  Extraction-cache validation:
    validate_extraction_cache
    write_extraction_diagnostics
  Temporal diversity metric:
    entropy_by_year
  Validation summary:
    generate_validation_summary

Constants:
  CROSSCUTTING_ENTROPY_THRESHOLD
  EXTRACTION_PROMPT, BENEFIT_EXTRACTION_PROMPT
  DEFAULT_TECH_WORDS, _SENTINELS
"""

from __future__ import annotations

import collections
import json
import logging
import random
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pub_dialogue.access import AccessStage

import numpy as np
import pandas as pd

logger = logging.getLogger("pub_dialogue.address")


# ---------------------------------------------------------------------------
# Proactive rate limiter
# ---------------------------------------------------------------------------

class _SlidingWindowLimiter:
    """Thread-safe sliding-window rate limiter.

    Blocks callers as needed so that no more than *max_calls* requests are
    issued within any rolling *window_seconds*-second window.
    """

    def __init__(self, max_calls: int = 450, window_seconds: float = 60.0) -> None:
        self._max = max_calls
        self._window = window_seconds
        self._times: collections.deque = collections.deque()
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block until a request slot is available, then claim it."""
        while True:
            with self._lock:
                now = time.time()
                # Expire timestamps outside the rolling window
                while self._times and now - self._times[0] > self._window:
                    self._times.popleft()
                if len(self._times) < self._max:
                    self._times.append(now)
                    return
                # Wait until the oldest token falls out of the window
                sleep_for = self._window - (now - self._times[0]) + 0.05
            time.sleep(sleep_for)


_rate_limiter: Optional[_SlidingWindowLimiter] = None


def configure_rate_limiter(calls_per_minute: int = 450) -> None:
    """Install a module-level rate limiter applied to every LLM call.

    Call this once after creating the LLMClient, before any extraction:

    .. code-block:: python

        import pub_dialogue.utils as du
        du.configure_rate_limiter(450)   # stay under 500 RPM hard limit

    Pass ``calls_per_minute=0`` to disable the limiter.
    """
    global _rate_limiter
    if calls_per_minute <= 0:
        _rate_limiter = None
        logger.info("Rate limiter disabled.")
    else:
        _rate_limiter = _SlidingWindowLimiter(max_calls=calls_per_minute)
        logger.info("Rate limiter configured: %d calls/min.", calls_per_minute)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CROSSCUTTING_ENTROPY_THRESHOLD: float = 0.5

# ---------------------------------------------------------------------------
# AddressStage — typed config dataclass (CIP-0010 Phase 1)
# ---------------------------------------------------------------------------

@dataclass
class AddressStage:
    """Configuration dataclass for the Address pipeline stage.

    Centralises all analysis constants that were previously hard-coded across
    every analysis notebook.  All existing module-level functions remain
    unchanged; this class provides a single place to inspect or override
    configuration.

    Usage in notebook setup cells::

        from pub_dialogue.access import AccessStage
        from pub_dialogue.address import AddressStage
        access  = AccessStage()
        address = AddressStage(access=access)
    """

    access: "AccessStage"
    n_concern_clusters: int = 75
    n_benefit_clusters: int = 75
    random_seed: int = 42
    tech_col: str = "technology_meta"
    ai_tech_label: str = "AI"
    cross_cutting_threshold: float = CROSSCUTTING_ENTROPY_THRESHOLD
    soft_membership_threshold: float = 0.3
    validation_sample_n: int = 250

    # -------------------------------------------------------------------
    # Year × cluster matrices (CIP-0009 document-level weighting)
    # -------------------------------------------------------------------

    def concern_year_matrix(
        self,
        phrases_df: "pd.DataFrame",
        chunks_df: "pd.DataFrame",
        technology: Optional[str] = None,
    ) -> "pd.DataFrame":
        """Return a year × cluster fraction matrix for concerns.

        Uses CIP-0009 document-level binary weighting (each document counted
        at most once per cluster per year).  Columns are all concern cluster IDs
        found in *phrases_df*, filled with 0.0 where absent.

        Parameters
        ----------
        phrases_df: concerns DataFrame (must have cluster_id, year, tech_col, source_file)
        chunks_df:  all chunks (must have year, tech_col, source_file)
        technology: technology label to filter by; defaults to ``ai_tech_label``
        """
        tech = technology if technology is not None else self.ai_tech_label
        result = temporal_cluster_frequency(
            phrases_df=phrases_df,
            chunks_df=chunks_df,
            kind="concern",
            tech_filter=tech,
            tech_col=self.tech_col,
        )
        all_clusters = sorted(
            phrases_df["cluster_id"].dropna().unique().astype(int).tolist()
        )
        return result.reindex(columns=all_clusters, fill_value=0.0)

    def benefit_year_matrix(
        self,
        phrases_df: "pd.DataFrame",
        chunks_df: "pd.DataFrame",
        technology: Optional[str] = None,
    ) -> "pd.DataFrame":
        """Return a year × cluster fraction matrix for benefits.

        Same document-level binary weighting as :meth:`concern_year_matrix`.
        """
        tech = technology if technology is not None else self.ai_tech_label
        result = temporal_cluster_frequency(
            phrases_df=phrases_df,
            chunks_df=chunks_df,
            kind="benefit",
            tech_filter=tech,
            tech_col=self.tech_col,
        )
        all_clusters = sorted(
            phrases_df["cluster_id"].dropna().unique().astype(int).tolist()
        )
        return result.reindex(columns=all_clusters, fill_value=0.0)

    # -------------------------------------------------------------------
    # PCA embedding trajectories
    # -------------------------------------------------------------------

    def _pca_trajectory(
        self,
        phrases_df: "pd.DataFrame",
        embeddings: "np.ndarray",
        phrase_ids: list,
        phrase_id_col: str,
        technology: Optional[str] = None,
    ) -> "pd.DataFrame":
        """Shared implementation for concern and benefit PCA trajectories."""
        from sklearn.decomposition import PCA

        tech = technology if technology is not None else self.ai_tech_label
        filtered = phrases_df[phrases_df[self.tech_col] == tech].copy()
        filtered = filtered.dropna(subset=["year"])
        filtered["year"] = filtered["year"].astype(int)

        id_to_idx = {pid: i for i, pid in enumerate(phrase_ids)}
        rows = []
        for yr, group in filtered.groupby("year"):
            idxs = [
                id_to_idx[pid]
                for pid in group[phrase_id_col]
                if pid in id_to_idx
            ]
            if not idxs:
                continue
            avg_emb = embeddings[np.array(idxs)].mean(axis=0)
            rows.append({"year": int(yr), "embedding": avg_emb})

        if not rows:
            return pd.DataFrame({"year": [], "pc1": [], "pc2": []})

        emb_matrix = np.stack([r["embedding"] for r in rows])
        n_comp = min(2, emb_matrix.shape[0])
        pca = PCA(n_components=n_comp)
        coords = pca.fit_transform(emb_matrix)
        return pd.DataFrame({
            "year": [r["year"] for r in rows],
            "pc1": coords[:, 0],
            "pc2": coords[:, 1] if n_comp > 1 else 0.0,
        })

    def concern_trajectory(
        self,
        phrases_df: "pd.DataFrame",
        embeddings: "np.ndarray",
        phrase_ids: list,
        technology: Optional[str] = None,
    ) -> "pd.DataFrame":
        """Compute per-year mean-embedding PCA trajectory for concerns.

        Parameters
        ----------
        phrases_df: concerns DataFrame (must have concern_id, year, tech_col)
        embeddings: numpy array of shape (n_phrases, embedding_dim)
        phrase_ids: ordered list of concern IDs matching ``embeddings`` rows
        technology: filter; defaults to ``ai_tech_label``

        Returns
        -------
        DataFrame with columns year, pc1, pc2 (one row per year)
        """
        return self._pca_trajectory(
            phrases_df, embeddings, phrase_ids, "concern_id", technology
        )

    def benefit_trajectory(
        self,
        phrases_df: "pd.DataFrame",
        embeddings: "np.ndarray",
        phrase_ids: list,
        technology: Optional[str] = None,
    ) -> "pd.DataFrame":
        """Compute per-year mean-embedding PCA trajectory for benefits.

        Same logic as :meth:`concern_trajectory` but for benefits.
        """
        return self._pca_trajectory(
            phrases_df, embeddings, phrase_ids, "benefit_id", technology
        )

    # -------------------------------------------------------------------
    # Per-technology cluster salience matrices
    # -------------------------------------------------------------------

    def _cluster_salience(
        self,
        phrases_df: "pd.DataFrame",
        phrase_id_col: str,
    ) -> "pd.DataFrame":
        """Shared implementation for concern/benefit salience."""
        technologies = sorted(
            phrases_df[self.tech_col].dropna().unique().tolist()
        )
        salience_by_tech: dict = {}
        for tech in technologies:
            mask = phrases_df[self.tech_col] == tech
            total = mask.sum()
            if total == 0:
                continue
            counts = phrases_df.loc[mask, "cluster_id"].value_counts()
            salience_by_tech[tech] = (counts / total).to_dict()

        result = pd.DataFrame(salience_by_tech).T.fillna(0)
        result.columns = result.columns.astype(int)
        return result

    def concern_salience(self, phrases_df: "pd.DataFrame") -> "pd.DataFrame":
        """Return a technology × cluster_id salience matrix for concerns.

        Each cell gives the fraction of that technology's concern phrases
        belonging to the cluster.  Rows sum to 1.0.

        Parameters
        ----------
        phrases_df: concerns DataFrame (must have cluster_id and tech_col)
        """
        return self._cluster_salience(phrases_df, "concern_id")

    def benefit_salience(self, phrases_df: "pd.DataFrame") -> "pd.DataFrame":
        """Return a technology × cluster_id salience matrix for benefits.

        Same structure as :meth:`concern_salience`.
        """
        return self._cluster_salience(phrases_df, "benefit_id")

DEFAULT_TECH_WORDS: List[str] = [
    "ai", "artificial intelligence", "nuclear", "genetic", "nano",
    "genome", "robot", "drone", "quantum", "gm", "embryo", "stem cell",
    "neural", "brain-computer",
]

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

# Illegal XML/XLSX character pattern (PDF extraction artefacts: control chars)
_ILLEGAL_XLSX_CHARS = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")


# ---------------------------------------------------------------------------
# ExtractionResult dataclass
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


# ---------------------------------------------------------------------------
# Phrase extraction
# ---------------------------------------------------------------------------

def _complete_with_retry(client, messages: list, max_tokens: int, max_retries: int = 5) -> str:
    """Call client.complete() with exponential backoff on RateLimitError.

    Parameters
    ----------
    client:
        :class:`~pub_dialogue.client.LLMClient` instance.
    messages:
        OpenAI-style message list.
    max_tokens:
        Passed through to ``client.complete``.
    max_retries:
        Maximum number of retry attempts after the first failure.

    Returns
    -------
    str
        The assistant reply text.

    Raises
    ------
    litellm.RateLimitError
        If all retries are exhausted.
    Any other exception
        Propagated immediately without retrying.
    """
    import litellm

    delay = 1.0
    for attempt in range(max_retries + 1):
        # Proactive throttle: block until a rate-limit slot is available
        if _rate_limiter is not None:
            _rate_limiter.wait()
        try:
            return client.complete(messages, max_tokens=max_tokens)
        except litellm.RateLimitError as exc:
            if attempt == max_retries:
                logger.warning(
                    "Rate limit: all %d retries exhausted — giving up.", max_retries
                )
                raise
            # Full jitter: spread retries across 0–delay so workers don't pile up
            sleep_for = random.uniform(0, delay)
            logger.debug(
                "Rate limit: attempt %d/%d, sleeping %.1fs before retry.",
                attempt + 1, max_retries, sleep_for,
            )
            time.sleep(sleep_for)
            delay = min(delay * 2, 60.0)


def extract_phrases(
    row_tuple,
    kind: str,
    client,
    tech_words: Optional[List[str]] = None,
    max_tokens: int = 500,
    max_retries: int = 5,
) -> ExtractionResult:
    """Extract decontextualised concern or benefit phrases from one paragraph.

    Parameters
    ----------
    row_tuple:
        ``(idx, row)`` tuple where ``row`` is a pandas Series with at least
        ``'chunk_id'`` and ``'text'`` fields.
    kind:
        ``'concern'`` or ``'benefit'``.
    client:
        :class:`~pub_dialogue.client.LLMClient` instance.
    tech_words:
        Substring filter list. Defaults to DEFAULT_TECH_WORDS.
    max_tokens:
        Maximum completion tokens.
    max_retries:
        Maximum retries on ``RateLimitError`` with exponential backoff.
        Defaults to 5.  Set to 0 to disable retry.

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

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt_template.format(text=str(row["text"])[:2000])},
    ]
    try:
        content = _complete_with_retry(client, messages, max_tokens, max_retries)
        if content is None:
            return ExtractionResult(chunk_id=chunk_id, sentinel_returned=True)

        content = content.strip()

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
        logger.warning("chunk %s: extraction failed — %s: %s", chunk_id, type(exc).__name__, exc)
        return ExtractionResult(
            chunk_id=chunk_id,
            error=f"{type(exc).__name__}: {exc}",
        )


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

def get_embeddings_batch(texts: List[str], client) -> np.ndarray:
    """Return a (len(texts), dim) array of embeddings.

    Parameters
    ----------
    texts:
        List of strings to embed.
    client:
        :class:`~pub_dialogue.client.LLMClient` instance.  The embedding
        model is configured on the client via ``embedding_model``.
    """
    return np.array(client.embed(texts))


# ---------------------------------------------------------------------------
# Cluster labelling
# ---------------------------------------------------------------------------

def label_cluster(
    cluster_id,
    exemplars: List[Dict[str, Any]],
    is_cross_cutting: bool,
    kind: str = "concern",
    client=None,
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
        :class:`~pub_dialogue.client.LLMClient` instance, or ``None`` to
        return the fallback label immediately.
    """
    if kind not in ("concern", "benefit"):
        raise ValueError(f"kind must be 'concern' or 'benefit', got {kind!r}")

    phrase_key = kind
    exemplar_texts = "\n".join(f"- {ex[phrase_key]}" for ex in exemplars[:8])
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
    fallback = {
        "label": f"Cluster {cluster_id}",
        "description": "",
        "key_terms": [],
        "success": False,
    }
    if client is None:
        return fallback
    messages = [
        {"role": "system", "content": "Expert qualitative researcher. Return only valid JSON."},
        {"role": "user", "content": prompt},
    ]
    try:
        content = client.complete(messages, max_tokens=1000)
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


def label_benefit_cluster(
    cluster_id,
    exemplars: List[Dict[str, Any]],
    is_cross_cutting: bool,
    client=None,
) -> Dict[str, Any]:
    """Generate a label for a benefit cluster with benefit-specific prompt guidance.

    Equivalent to :func:`label_cluster` with ``kind='benefit'``, but uses
    more explicit prompt language to discourage technology-prefixed labels
    (e.g. produces "Improved diagnosis" not "AI-driven improved diagnosis").

    Parameters
    ----------
    cluster_id:
        Cluster identifier.
    exemplars:
        List of dicts with a ``'benefit'`` key.
    is_cross_cutting:
        Whether the cluster spans multiple technologies.
    client:
        :class:`~pub_dialogue.client.LLMClient` instance, or ``None`` for
        fallback.
    """
    exemplar_texts = "\n".join(f"- {ex['benefit']}" for ex in exemplars[:8])
    prompt = (
        f"Analyze this cluster of public benefits from UK dialogue reports.\n\n"
        f"Benefit phrases in this cluster:\n{exemplar_texts}\n\n"
        "Provide:\n"
        "1. SHORT LABEL (3-6 words) capturing the core benefit theme.\n"
        "   Use neutral, generic language; do NOT prefix the label with a specific\n"
        "   technology (e.g. write \"Improved diagnosis\", not \"AI-driven improved diagnosis\").\n"
        "2. DESCRIPTION (1-2 sentences)\n"
        "3. KEY TERMS (3-5 representative words/phrases)\n\n"
        'Return JSON only:\n{"label": "...", "description": "...", "key_terms": ["...", "..."]}'
    )
    fallback = {
        "label": f"Cluster {cluster_id}",
        "description": "",
        "key_terms": [],
        "success": False,
    }
    if client is None:
        return fallback
    messages = [
        {"role": "system", "content": "Expert qualitative researcher. Return only valid JSON."},
        {"role": "user", "content": prompt},
    ]
    try:
        content = client.complete(messages, max_tokens=1000)
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


# ---------------------------------------------------------------------------
# AI fingerprint metric
# ---------------------------------------------------------------------------

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
    other_mean = (
        shares[other_cols].mean(axis=1)
        if other_cols
        else pd.Series(0, index=shares.index)
    )
    return (ai_share - other_mean).sort_values(ascending=False)


# ---------------------------------------------------------------------------
# Sensitivity analysis
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

    Replaces the notebook's duplicate ``run_for_k`` definitions.  Output
    filenames are prefixed with ``{kind}_sensitivity_`` so concern and benefit
    runs never overwrite each other.

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
        raise ImportError(
            "scikit-learn and matplotlib are required for sensitivity analysis."
        ) from exc

    if kind not in ("concern", "benefit"):
        raise ValueError(f"kind must be 'concern' or 'benefit', got {kind!r}")

    if phrase_col is None:
        phrase_col = kind

    from pub_dialogue.utils import normalized_entropy, parse_year  # avoid circular import

    output_folder = Path(output_folder)
    prefix = f"{kind}_sensitivity"

    km = KMeans(n_clusters=k, random_state=random_seed, n_init="auto")
    labels = km.fit_predict(embeddings_normalized)

    run_df = df.copy()
    run_df["cluster_id_k"] = labels

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
    ai_candidates = [
        c for c in prof_df.index
        if str(c).strip().lower() in ("ai", "artificial intelligence")
    ]

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

        html_content = (
            f"<h2>AI {kind.capitalize()} Fingerprint (k={k})</h2>\n"
            + fingerprint_df.to_html(index=False)
        )
        (output_folder / f"{prefix}_fingerprint_k{k}.html").write_text(html_content)

    time_df = run_df.copy()
    time_df["__year__"] = time_df.get("year", pd.Series(dtype=object)).apply(parse_year)
    time_df = time_df.dropna(subset=["__year__"])
    time_df["__year__"] = time_df["__year__"].astype(int)

    ai_mask = time_df[tech_col].astype(str).str.strip().str.lower().isin(
        ("ai", "artificial intelligence")
    )
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

            html_content = (
                f"<h2>{kind.capitalize()} Lens Salience (k={k})</h2>\n"
                + lens_df.to_html(index=False)
            )
            (output_folder / f"{prefix}_radar_k{k}.html").write_text(html_content)


# ---------------------------------------------------------------------------
# Temporal analysis helpers
# ---------------------------------------------------------------------------

def assign_window(year) -> Optional[str]:
    """Map a year value to a broad time window string.

    Returns one of ``"2004-2017"``, ``"2018-2020"``, ``"2021-2023"``,
    ``"2024-2025"``, or ``None`` if *year* is NaN/missing.
    """
    if year is None:
        return None
    try:
        import pandas as _pd
        if _pd.isna(year):
            return None
    except Exception:
        pass
    y = int(year)
    if y <= 2017:
        return "2004-2017"
    if y <= 2020:
        return "2018-2020"
    if y <= 2023:
        return "2021-2023"
    return "2024-2025"


def _parse_listcol(s) -> list:
    """Parse a stringified list column (e.g. from CSV round-trip) into a Python list.

    Handles both JSON-format (``["a", "b"]``) and repr-format (``['a', 'b']``).
    Returns an empty list for NaN / empty / ``"[]"`` values.
    """
    if s is None:
        return []
    try:
        import pandas as _pd
        if _pd.isna(s):
            return []
    except Exception:
        pass
    s = str(s).strip()
    if not s or s == "[]":
        return []
    try:
        return json.loads(s.replace("'", '"'))
    except Exception:
        s = s.strip("[]")
        return [x.strip().strip("'\"") for x in s.split(",")] if s else []


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
        raise ValueError(
            "Expected a paragraph id column (paragraph_id, para_id, or chunk_id)."
        )
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
        counts = counts.merge(
            summary_df[["cluster_id", "label"]], on="cluster_id", how="left"
        )
    counts.insert(0, "kind", kind)
    return counts


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def _clean_for_xlsx(v: Any) -> Any:
    """Strip control characters that openpyxl refuses to write.

    These are PDF-extraction artefacts (vertical tabs, form feeds, etc.) and
    carry no semantic content.  Pass a DataFrame through this with
    ``df.applymap(_clean_for_xlsx)`` before calling ``.to_excel()``.
    """
    if isinstance(v, str):
        return _ILLEGAL_XLSX_CHARS.sub("", v)
    return v


# ---------------------------------------------------------------------------
# Extraction-cache validation
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
        List of :class:`ExtractionResult` objects.
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
    pd.DataFrame(error_rows, columns=["chunk_id", "track", "error"]).to_csv(
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
# Temporal diversity metric
# ---------------------------------------------------------------------------

def entropy_by_year(g: pd.DataFrame, cluster_col: str = "cluster_id") -> float:
    """Normalised entropy of cluster distribution within a year-group.

    Operates on address-stage outputs (clusters are produced by k-means on
    extracted phrase embeddings).  Intended for use with
    ``groupby(...).apply(entropy_by_year)``.
    """
    from pub_dialogue.utils import normalized_entropy  # avoid circular import
    p = g[cluster_col].value_counts(normalize=True).values
    return normalized_entropy(p)


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

    lines += ["", "Generated by pub_dialogue.address.generate_validation_summary()"]

    out_path = output_folder / "validation_summary.txt"
    out_path.write_text("\n".join(lines))
    print(f"Validation summary written to {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Temporal cluster frequency — document-level weighting (CIP-0009, Approach B)
# ---------------------------------------------------------------------------

def temporal_cluster_frequency(
    phrases_df: "pd.DataFrame",
    chunks_df: "pd.DataFrame",
    kind: str,
    tech_filter: Optional[str] = None,
    tech_col: str = "technology_meta",
    doc_col: str = "source_file",
    year_col: str = "year",
    cluster_col: str = "cluster_id",
) -> "pd.DataFrame":
    """Return document-weighted temporal cluster frequency (CIP-0009 Approach B).

    **Methodology (Approach B — selected 2026-05-13):**
    For each ``(year, cluster_id)`` the value is the *fraction of documents in
    that year* that mention at least one phrase assigned to that cluster.  This
    removes two confounds present in raw phrase counts:

    * **Volume bias**: years with more dialogues conducted would otherwise
      dominate raw counts regardless of what participants said.
    * **Length bias**: longer documents contribute more phrases and therefore
      appear more prominent than shorter documents on the same topic.

    The result can be interpreted as "what percentage of AI public dialogue
    documents published in year Y raised concern/benefit cluster C?".

    Parameters
    ----------
    phrases_df:
        ``concerns_df`` or ``benefits_df`` with at least ``chunk_id`` and
        *cluster_col* columns.
    chunks_df:
        ``paragraph_chunks`` DataFrame with ``chunk_id``, *doc_col*, *year_col*,
        and *tech_col* columns.
    kind:
        ``'concern'`` or ``'benefit'`` (used for validation only).
    tech_filter:
        If provided, restrict to documents whose *tech_col* equals this value
        (e.g. ``'AI'``).
    tech_col:
        Column name for technology labels in *chunks_df*.
    doc_col:
        Column name for document identifier in *chunks_df* (default
        ``'source_file'``).
    year_col:
        Column name for year in *chunks_df* (default ``'year'``).
    cluster_col:
        Column name for cluster assignment in *phrases_df* (default
        ``'cluster_id'``).

    Returns
    -------
    pd.DataFrame
        Index = year (int), columns = cluster_id (int), values = fraction of
        documents in that year mentioning that cluster (float 0–1).
    """
    import pandas as pd

    if kind not in ("concern", "benefit"):
        raise ValueError(f"kind must be 'concern' or 'benefit', got {kind!r}")

    # Join phrases → chunks to get document identifier and year
    needed_cols = [c for c in [doc_col, year_col, tech_col, "chunk_id"] if c in chunks_df.columns]
    merged = phrases_df[[cluster_col, "chunk_id"]].merge(
        chunks_df[needed_cols], on="chunk_id", how="left"
    )

    # Optional technology filter
    if tech_filter is not None and tech_col in merged.columns:
        merged = merged[merged[tech_col] == tech_filter]

    merged = merged.dropna(subset=[year_col, cluster_col, doc_col])
    merged[year_col] = merged[year_col].astype(int)
    merged[cluster_col] = merged[cluster_col].astype(int)

    if merged.empty:
        return pd.DataFrame()

    # --- Document-level binary presence per (doc, cluster) ---
    # One row per unique (year, doc, cluster) — binary: doc mentions cluster
    doc_cluster = (
        merged[[year_col, doc_col, cluster_col]]
        .drop_duplicates()
    )

    # Total documents per year (denominator)
    docs_per_year = (
        chunks_df.copy()
        .pipe(lambda df: df[df[tech_col] == tech_filter] if tech_filter and tech_col in df.columns else df)
        .dropna(subset=[year_col, doc_col])
        .assign(**{year_col: lambda df: df[year_col].astype(int)})
        [[year_col, doc_col]]
        .drop_duplicates()
        .groupby(year_col)[doc_col]
        .count()
        .rename("n_docs")
    )

    # Count documents per (year, cluster) that mention cluster
    docs_mentioning = (
        doc_cluster
        .groupby([year_col, cluster_col])[doc_col]
        .count()
        .reset_index()
        .rename(columns={doc_col: "n_docs_mentioning"})
    )

    # Pivot: rows = year, cols = cluster_id
    pivot = docs_mentioning.pivot(index=year_col, columns=cluster_col, values="n_docs_mentioning")

    # Normalise each year by total docs in that year
    pivot = pivot.div(docs_per_year, axis=0).fillna(0.0)
    pivot.index.name = "year"
    pivot.columns.name = None

    return pivot


# ---------------------------------------------------------------------------
# Prompt sensitivity analysis (CIP-0008)
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT_B = """Identify the specific anxieties, objections, or reservations expressed \
in this paragraph.

CRITICAL RULES:
1. Remove ALL technology-specific references (AI, nuclear, genetic, nano, etc.)
2. Capture the underlying worry that could apply to ANY emerging technology
3. Keep phrases concise (3-10 words each)
4. Focus on fears and objections, not factual statements
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

EXTRACTION_PROMPT_C = """List the public concerns in this paragraph. \
Be concise (3-8 words per phrase). Return one concern per line.
Return NO_CONCERN if the paragraph expresses no concerns.

Paragraph:
{text}"""

BENEFIT_EXTRACTION_PROMPT_B = """Identify the hoped-for gains, opportunities, or positive outcomes \
expressed in this paragraph.

CRITICAL RULES:
1. Remove ALL technology-specific references (AI, nuclear, genetic, nano, etc.)
2. Capture the underlying benefit that could apply to ANY emerging technology
3. Keep each phrase concise (3-10 words)
4. Prefer concrete impacts over vague praise
5. Do NOT include concerns, caveats, or neutral facts
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

BENEFIT_EXTRACTION_PROMPT_C = """List the public benefits expressed in this paragraph. \
Be concise (3-8 words per phrase). Return one benefit per line.
Return NO_BENEFIT if the paragraph expresses no benefits.

Paragraph:
{text}"""

CONCERN_PROMPT_VARIANTS: Dict[str, str] = {
    "A_current": EXTRACTION_PROMPT,
    "B_paraphrase": EXTRACTION_PROMPT_B,
    "C_minimal": EXTRACTION_PROMPT_C,
}

BENEFIT_PROMPT_VARIANTS: Dict[str, str] = {
    "A_current": BENEFIT_EXTRACTION_PROMPT,
    "B_paraphrase": BENEFIT_EXTRACTION_PROMPT_B,
    "C_minimal": BENEFIT_EXTRACTION_PROMPT_C,
}


def run_prompt_sensitivity(
    chunks: "pd.DataFrame",
    kind: str,
    prompts: Optional[Dict[str, str]] = None,
    client=None,
    sample_n: int = 200,
    random_seed: int = 42,
    output_folder: Optional[Path] = None,
    tech_col: str = "technology_meta",
    max_tokens: int = 300,
) -> "pd.DataFrame":
    """Run extraction with multiple prompt variants and measure inter-prompt agreement.

    For each pair of variants the function reports:

    * **yield_agreement** — fraction of sampled chunks where both variants
      agree on whether a phrase was extracted (both non-sentinel or both sentinel).
    * **phrase_agreement** — among chunks where both variants extracted ≥1
      phrase, the mean fraction of phrases in variant A that have a semantic
      near-match (cosine similarity ≥ 0.85) in variant B, averaged
      symmetrically.

    Parameters
    ----------
    chunks:
        DataFrame with at least ``'chunk_id'``, ``'text'``, and *tech_col*
        columns (typically ``paragraph_chunks.csv``).
    kind:
        ``'concern'`` or ``'benefit'``.
    prompts:
        Dict mapping variant name → prompt template string (with ``{text}``
        placeholder).  Defaults to :data:`CONCERN_PROMPT_VARIANTS` or
        :data:`BENEFIT_PROMPT_VARIANTS`.
    client:
        :class:`~pub_dialogue.client.LLMClient` instance.
    sample_n:
        Number of chunks to sample (stratified by technology).
    random_seed:
        Random state for sampling and reproducibility.
    output_folder:
        If provided, writes ``prompt_sensitivity_report_{kind}.csv`` and
        ``prompt_sensitivity_summary_{kind}.txt``.
    tech_col:
        Column name for technology labels (used for stratified sampling).
    max_tokens:
        Maximum completion tokens per extraction call.

    Returns
    -------
    pd.DataFrame
        One row per variant-pair with columns ``variant_a``, ``variant_b``,
        ``yield_agreement``, ``phrase_agreement``, ``n_chunks``.
    """
    import numpy as np
    import pandas as pd

    if kind not in ("concern", "benefit"):
        raise ValueError(f"kind must be 'concern' or 'benefit', got {kind!r}")

    if prompts is None:
        prompts = CONCERN_PROMPT_VARIANTS if kind == "concern" else BENEFIT_PROMPT_VARIANTS

    sentinel = f"NO_{kind.upper()}"
    system_msg = (
        "Extract public concerns. Be concise. Remove technology-specific language."
        if kind == "concern"
        else "Extract public benefits. Be concise. Remove technology-specific language."
    )

    # --- Stratified sample -----------------------------------------------
    rng = np.random.default_rng(random_seed)
    if tech_col in chunks.columns:
        techs = chunks[tech_col].dropna().unique()
        per_tech = max(1, sample_n // len(techs))
        parts = []
        for tech in techs:
            grp = chunks[chunks[tech_col] == tech]
            n = min(per_tech, len(grp))
            idx = rng.choice(len(grp), size=n, replace=False)
            parts.append(grp.iloc[idx])
        sample = pd.concat(parts).drop_duplicates(subset="chunk_id").head(sample_n)
    else:
        idx = rng.choice(len(chunks), size=min(sample_n, len(chunks)), replace=False)
        sample = chunks.iloc[idx]

    # --- Extract phrases for each variant ---------------------------------
    variant_results: Dict[str, Dict[str, list]] = {}  # variant → {chunk_id: [phrases]}
    for variant_name, prompt_template in prompts.items():
        print(f"  [{kind}] variant {variant_name!r}: extracting from {len(sample)} chunks…")
        results: Dict[str, list] = {}
        for _, row in sample.iterrows():
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt_template.format(text=str(row["text"])[:2000])},
            ]
            try:
                content = client.complete(messages, max_tokens=max_tokens).strip()
            except Exception:
                content = sentinel
            if not content or content in _SENTINELS:
                results[row["chunk_id"]] = []
            else:
                phrases = [
                    ln.strip()
                    for ln in content.split("\n")
                    if ln.strip() and ln.strip() not in _SENTINELS
                ]
                results[row["chunk_id"]] = phrases
        variant_results[variant_name] = results

    # --- Compute pairwise agreement ---------------------------------------
    variant_names = list(prompts.keys())
    rows = []
    for i, va in enumerate(variant_names):
        for vb in variant_names[i + 1:]:
            ra, rb = variant_results[va], variant_results[vb]
            chunk_ids = list(sample["chunk_id"])
            n = len(chunk_ids)

            # Yield agreement: both flag ≥1 phrase, or both sentinel
            yield_agree = sum(
                (bool(ra.get(c)) == bool(rb.get(c))) for c in chunk_ids
            ) / n

            # Phrase agreement: embed and compute cosine sim
            both_extracted = [
                c for c in chunk_ids if ra.get(c) and rb.get(c)
            ]
            phrase_agree = float("nan")
            if both_extracted and client is not None:
                all_a = [p for c in both_extracted for p in ra[c]]
                all_b = [p for c in both_extracted for p in rb[c]]
                unique_phrases = list(dict.fromkeys(all_a + all_b))
                if unique_phrases:
                    try:
                        vecs = np.array(client.embed(unique_phrases))
                        # normalise
                        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
                        norms[norms == 0] = 1
                        vecs = vecs / norms
                        phrase_idx = {p: i for i, p in enumerate(unique_phrases)}

                        match_fracs = []
                        for c in both_extracted:
                            idx_a = [phrase_idx[p] for p in ra[c] if p in phrase_idx]
                            idx_b = [phrase_idx[p] for p in rb[c] if p in phrase_idx]
                            if not idx_a or not idx_b:
                                continue
                            sim = vecs[idx_a] @ vecs[idx_b].T  # (|a|, |b|)
                            matched_a = float((sim.max(axis=1) >= 0.85).mean())
                            matched_b = float((sim.max(axis=0) >= 0.85).mean())
                            match_fracs.append((matched_a + matched_b) / 2)
                        if match_fracs:
                            phrase_agree = float(np.mean(match_fracs))
                    except Exception:
                        pass  # embedding unavailable; leave as nan

            rows.append(
                {
                    "variant_a": va,
                    "variant_b": vb,
                    "yield_agreement": round(yield_agree, 4),
                    "phrase_agreement": round(phrase_agree, 4) if not (isinstance(phrase_agree, float) and phrase_agree != phrase_agree) else None,
                    "n_chunks": n,
                    "n_both_extracted": len(both_extracted),
                }
            )
            print(
                f"    {va} vs {vb}: yield={yield_agree:.1%}  "
                f"phrase={phrase_agree:.1%}" if phrase_agree == phrase_agree  # noqa: PLR0124
                else f"    {va} vs {vb}: yield={yield_agree:.1%}  phrase=n/a"
            )

    report = pd.DataFrame(rows)

    if output_folder is not None:
        output_folder = Path(output_folder)
        csv_path = output_folder / f"prompt_sensitivity_report_{kind}.csv"
        report.to_csv(csv_path, index=False)
        print(f"  Report written to {csv_path}")

        thresholds = {"yield_agreement": 0.85, "phrase_agreement": 0.70}
        lines = [
            f"Prompt sensitivity summary — {kind}",
            f"Sample size: {len(sample)} chunks, {len(prompts)} variants",
            "",
        ]
        for _, r in report.iterrows():
            y_ok = r["yield_agreement"] >= thresholds["yield_agreement"]
            p_val = r["phrase_agreement"]
            p_ok = (p_val is not None and p_val >= thresholds["phrase_agreement"])
            lines += [
                f"{r['variant_a']} vs {r['variant_b']}:",
                f"  yield_agreement  = {r['yield_agreement']:.1%}  "
                f"({'OK' if y_ok else 'BELOW THRESHOLD ≥85%'})",
                f"  phrase_agreement = {p_val:.1%}  "
                f"({'OK' if p_ok else 'BELOW THRESHOLD ≥70%'})"
                if p_val is not None else "  phrase_agreement = n/a",
                "",
            ]
        txt_path = output_folder / f"prompt_sensitivity_summary_{kind}.txt"
        txt_path.write_text("\n".join(lines))
        print(f"  Summary written to {txt_path}")

    return report
