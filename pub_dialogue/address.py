"""
pub_dialogue.address — Research-question-specific analysis stage.

This module owns everything that requires knowledge of the research question: LLM-based
phrase extraction, embedding generation, clustering, labelling, and downstream analysis.
All functions here operate on the outputs of the access and assess stages.

Public API:
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
from typing import Any, Dict, List, Optional

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
