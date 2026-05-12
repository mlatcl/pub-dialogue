# dialogue_utils.py — backward-compatibility shim.
# The canonical module is pub_dialogue.utils.
# This file exists so that existing `import dialogue_utils as du` calls
# continue to work without modification.
from pub_dialogue.utils import *  # noqa: F401, F403
from pub_dialogue.utils import (  # noqa: F401 (ensure private names available)
    _volume_table,
    _top_clusters,
    _chunk_stats,
    _extract_paragraphs_from_blocks,
    _paragraph_split,
    _split_into_sentences,
    _repack_sentences_into_chunks,
)
