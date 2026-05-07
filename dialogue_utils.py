"""
dialogue_utils.py — Shared utilities for the public dialogue analyser pipeline.

This module consolidates all helper functions that were previously duplicated
across concern and benefit sections of the notebook. The notebook imports this
module and calls functions via `import dialogue_utils as du`.

Public API (grouped by responsibility):
  I/O & display:
    show_status, show_complete, show_warning
    save_checkpoint, load_checkpoint
  Corpus ingestion:
    extract_chunks_from_pdf
  Extraction:
    ExtractionResult (dataclass)
    extract_phrases
  Embeddings:
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
  META_VOCABULARY      — meta-vocabulary stop-list for CIP-0004 diagnostics
  PRIVACY_TERMS        — keywords for privacy-cluster detection
  EXTRACTION_PROMPT    — LLM prompt template for concern extraction
  BENEFIT_EXTRACTION_PROMPT — LLM prompt template for benefit extraction
"""

from __future__ import annotations

import html as _html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
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


# ---------------------------------------------------------------------------
# Corpus ingestion
# ---------------------------------------------------------------------------

def extract_chunks_from_pdf(
    pdf_path: Path,
    metadata: Dict[str, Any],
    min_chunk_words: int = 50,
    min_chunk_chars: int = 100,
    max_chunk_words: int = 400,
) -> List[Dict[str, Any]]:
    """Extract paragraph-level text chunks from a single PDF.

    Parameters
    ----------
    pdf_path:
        Path to the PDF file.
    metadata:
        Dict with at least 'technology' and 'year' keys.
    min_chunk_words, min_chunk_chars, max_chunk_words:
        Length filters; paragraphs shorter than the minimums are kept in the
        output dataframe but will rarely yield extraction results.

    Returns
    -------
    list of dicts, one per paragraph.
    """
    try:
        import fitz  # type: ignore  # PyMuPDF
    except ImportError as exc:
        raise ImportError("PyMuPDF (fitz) is required for PDF extraction.") from exc

    chunks: List[Dict[str, Any]] = []
    try:
        doc = fitz.open(pdf_path)
        full_text = "".join(page.get_text() for page in doc)
        doc.close()

        paragraphs = re.split(r"\n\s*\n", full_text)
        for i, para in enumerate(paragraphs):
            para = re.sub(r"\s+", " ", para).strip()
            word_count = len(para.split())
            if word_count >= min_chunk_words and len(para) >= min_chunk_chars:
                words = para.split()
                if len(words) > max_chunk_words:
                    para = " ".join(words[:max_chunk_words])
            chunks.append({
                "text": para,
                "source_file": Path(pdf_path).name,
                "chunk_index": i,
                "word_count": len(para.split()),
                "technology": metadata.get("technology", "Unknown"),
                "technology_meta": metadata.get("technology", "Unknown"),
                "year": metadata.get("year", None),
            })
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
            match = next(
                (tw for tw in tech_words if tw in phrase.lower()), None
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


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

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
        f"- {ex[phrase_key]} (from {ex.get('technology', 'Unknown')})"
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
        from scipy.stats import entropy as shannon_entropy  # type: ignore
        import matplotlib.pyplot as plt  # type: ignore
    except ImportError as exc:
        raise ImportError("scikit-learn, scipy, and matplotlib are required for sensitivity analysis.") from exc

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
        probs = (tech_counts / tech_counts.sum()).values if tech_counts.sum() > 0 else np.array([])
        ent[cid] = float(shannon_entropy(probs)) if len(probs) > 1 else 0.0

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
