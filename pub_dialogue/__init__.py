"""
pub_dialogue — Public Dialogue Analyser shared utilities and pipeline.

The package is organised around the access / assess / address pipeline framework:

* :mod:`pub_dialogue.access`  — PDF ingestion, chunking, artefact loading.
* :mod:`pub_dialogue.assess`  — Question-agnostic data quality and diagnostics.
* :mod:`pub_dialogue.address` — LLM extraction, embeddings, clustering, analysis.
* :mod:`pub_dialogue.utils`   — Shared helpers + backward-compatibility re-exports.
* :mod:`pub_dialogue.client`  — LLM client abstraction.

Import convention in notebooks::

    import pub_dialogue.utils as du
    # or import the stage modules directly:
    import pub_dialogue.access as access
    import pub_dialogue.assess as assess
    import pub_dialogue.address as address

Key names are also available directly from this package::

    from pub_dialogue import normalized_entropy, load_artifacts, extract_phrases
"""

__version__ = "0.1.0"

# Stage submodules — import them so they are accessible as attributes
from pub_dialogue import access  # noqa: F401
from pub_dialogue import assess  # noqa: F401
from pub_dialogue import address  # noqa: F401

from pub_dialogue.client import LLMClient  # noqa: F401

# Convenience re-exports of the most-used names (all sourced via utils for
# backward compatibility; utils itself re-exports from the stage modules)
from pub_dialogue.utils import (  # noqa: F401
    # Display
    show_status,
    show_complete,
    show_warning,
    # Access-stage
    save_checkpoint,
    load_checkpoint,
    load_artifacts,
    extract_chunks_from_pdf,
    reset_chunk_stats,
    get_chunk_stats,
    # Address-stage extraction
    ExtractionResult,
    extract_phrases,
    # Assess-stage quality
    validate_extraction_cache,
    filter_missing_source_text,
    # Address-stage embeddings + clustering
    get_embeddings_batch,
    label_cluster,
    # Utils formatting
    pretty_label,
    clusters_to_labels,
    clusters_to_lenses,
    # Pure maths
    normalized_entropy,
    hhi,
    topk_share,
    parse_year,
    tokenize,
    # Metrics
    entropy_by_year,
    ai_fingerprint_over_crosscut,
    # Sensitivity
    run_sensitivity,
    # Comparison helpers
    _volume_table,
    _top_clusters,
    # Constants
    CROSSCUTTING_ENTROPY_THRESHOLD,
    MIN_CHUNK_WORDS,
    MAX_CHUNK_WORDS,
    MIN_CHUNK_CHARS,
    SENTENCE_FALLBACK_TARGET_WORDS,
    SENTENCE_FALLBACK_MIN_PARAGRAPHS,
    EXTRACTION_PROMPT,
    BENEFIT_EXTRACTION_PROMPT,
)
