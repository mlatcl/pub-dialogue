"""
pub_dialogue — Public Dialogue Analyser shared utilities and pipeline.

Import convention in notebooks::

    import pub_dialogue.utils as du

Key functions are also available directly from this package::

    from pub_dialogue import normalized_entropy, load_artifacts
"""

__version__ = "0.1.0"

# Convenience re-exports of the most-used names
from pub_dialogue.utils import (  # noqa: F401
    # I/O
    show_status,
    show_complete,
    show_warning,
    save_checkpoint,
    load_checkpoint,
    load_artifacts,
    # Corpus ingestion
    extract_chunks_from_pdf,
    reset_chunk_stats,
    get_chunk_stats,
    # Extraction
    ExtractionResult,
    extract_phrases,
    validate_extraction_cache,
    # Embeddings
    filter_missing_source_text,
    get_embeddings_batch,
    # Cluster semantics
    label_cluster,
    pretty_label,
    clusters_to_labels,
    clusters_to_lenses,
    # Utilities
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
