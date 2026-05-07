"""Refactor notebook to import from dialogue_utils, fix sensitivity cells, strip outputs."""
import json, re, sys
from pathlib import Path

NB_PATH = Path("public_dialogue_analyser_v12b_4.ipynb")
OUT_PATH = NB_PATH  # overwrite in place

with open(NB_PATH) as f:
    nb = json.load(f)

cells = nb["cells"]

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def set_source(cell, lines):
    """Replace a cell's source list with lines (as a single string or list)."""
    if isinstance(lines, list):
        cell["source"] = lines
    else:
        cell["source"] = [lines]

def strip_outputs(cell):
    if cell["cell_type"] == "code":
        cell["outputs"] = []
        cell["execution_count"] = None

# ---------------------------------------------------------------------------
# 1. Strip ALL outputs
# ---------------------------------------------------------------------------
for c in cells:
    strip_outputs(c)

# ---------------------------------------------------------------------------
# 2. Cell 4 — add `from dialogue_utils import *` after imports
# ---------------------------------------------------------------------------
src4 = "".join(cells[4]["source"])
# Append after the existing import block
if "from dialogue_utils import" not in src4:
    src4 = src4.rstrip() + "\n\nfrom dialogue_utils import *  # noqa: F401,F403\n"
set_source(cells[4], src4)

# ---------------------------------------------------------------------------
# 3. Pure-definition cells — replace with a comment
# ---------------------------------------------------------------------------
PURE_DEF_CELLS = {
    5:   "# show_status, show_complete, show_warning, save_checkpoint, load_checkpoint\n# — imported from dialogue_utils",
    11:  "# extract_chunks_from_pdf — imported from dialogue_utils",
    18:  "# get_embeddings_batch — imported from dialogue_utils",
    24:  "# label_cluster (concerns) — imported from dialogue_utils",
    39:  "# pretty_label (concerns) — imported from dialogue_utils",
    41:  "# normalized_entropy, hhi, topk_share, parse_year (concerns) — imported from dialogue_utils",
    63:  "# label_cluster (benefits) — duplicate removed; imported from dialogue_utils",
    78:  "# pretty_label (benefits) — duplicate removed; imported from dialogue_utils",
    80:  "# normalized_entropy, hhi, topk_share, parse_year (benefits) — duplicate removed; imported from dialogue_utils",
    92:  "# _volume_table — imported from dialogue_utils",
    93:  "# _top_clusters — imported from dialogue_utils",
    98:  "# clusters_to_labels, clusters_to_lenses, html_escape — imported from dialogue_utils",
    99:  "# normalized_entropy, ai_fingerprint_over_crosscut — imported from dialogue_utils",
    101: "# parse_year, tokenize — imported from dialogue_utils",
    105: "# parse_year, normalized_entropy, is_privacy_text, entropy_by_year (concerns) — imported from dialogue_utils",
    108: "# clusters_to_labels, clusters_to_lenses, html_escape (benefits) — duplicate removed; imported from dialogue_utils",
    109: "# normalized_entropy, ai_fingerprint_over_crosscut (benefits) — duplicate removed; imported from dialogue_utils",
    111: "# parse_year, tokenize (benefits) — duplicate removed; imported from dialogue_utils",
    115: "# parse_year, normalized_entropy, is_privacy_text, entropy_by_year (benefits) — imported from dialogue_utils",
}
for idx, comment in PURE_DEF_CELLS.items():
    set_source(cells[idx], comment + "\n")

# ---------------------------------------------------------------------------
# 4. Cell 57 — remove inline get_embeddings_batch guard (already in module)
# ---------------------------------------------------------------------------
src57 = "".join(cells[57]["source"])
# Remove the "if get_embeddings_batch not in globals(): def get_embeddings_batch..." block
guard_pat = re.compile(
    r'# Reuse get_embeddings_batch.*?^(?=\n[^\s])',
    re.DOTALL | re.MULTILINE,
)
src57_new = guard_pat.sub(
    "# get_embeddings_batch imported from dialogue_utils\n",
    src57,
)
if src57_new != src57:
    set_source(cells[57], src57_new)

# ---------------------------------------------------------------------------
# 5. Cell 14 — concerns extraction: remove function def, update calls
# ---------------------------------------------------------------------------
src14 = "".join(cells[14]["source"])

# a) Remove EXTRACTION_PROMPT constant block (from start to just before def)
src14 = re.sub(
    r'EXTRACTION_PROMPT\s*=\s*""".*?"""\s*\n',
    "# CONCERN_PROMPT is defined in dialogue_utils (includes anti-artefact rules)\n",
    src14,
    flags=re.DOTALL,
)

# b) Remove def extract_concerns_from_paragraph(row_tuple): ... (up to blank line after return)
src14 = re.sub(
    r'def extract_concerns_from_paragraph\(row_tuple\):.*?return row\[.chunk_id.\], filtered\s*\n',
    "# extract_concerns_from_paragraph replaced by extract_phrases(row, kind='concern', ...) from dialogue_utils\n",
    src14,
    flags=re.DOTALL,
)

# c) Update executor.submit call
src14 = src14.replace(
    "executor.submit(extract_concerns_from_paragraph, row)",
    "executor.submit(extract_phrases, row, 'concern', client, None, LLM_MODEL)",
)

# d) Update result unpacking (old: chunk_id, concerns = future.result())
src14 = src14.replace(
    "chunk_id, concerns = future.result()",
    "_result = future.result()\n            chunk_id, concerns = _result.chunk_id, _result.retained_phrases",
)

set_source(cells[14], src14)

# ---------------------------------------------------------------------------
# 6. Cell 53 — benefits extraction: same pattern
# ---------------------------------------------------------------------------
src53 = "".join(cells[53]["source"])

# a) Remove BENEFIT_EXTRACTION_PROMPT
src53 = re.sub(
    r'BENEFIT_EXTRACTION_PROMPT\s*=\s*""".*?"""\s*\n',
    "# BENEFIT_PROMPT is defined in dialogue_utils (includes anti-artefact rules)\n",
    src53,
    flags=re.DOTALL,
)

# b) Remove def extract_benefits_from_paragraph(...)
src53 = re.sub(
    r'def extract_benefits_from_paragraph\(row_tuple\):.*?return row\["chunk_id"\], filtered\s*\n',
    "# extract_benefits_from_paragraph replaced by extract_phrases(row, kind='benefit', ...) from dialogue_utils\n",
    src53,
    flags=re.DOTALL,
)

# c) Update executor.submit call
src53 = src53.replace(
    'executor.submit(extract_benefits_from_paragraph, row)',
    "executor.submit(extract_phrases, row, 'benefit', client, None, LLM_MODEL)",
)

# d) Update result unpacking
src53 = src53.replace(
    "chunk_id, benefits = future.result()",
    "_result = future.result()\n            chunk_id, benefits = _result.chunk_id, _result.retained_phrases",
)

set_source(cells[53], src53)

# ---------------------------------------------------------------------------
# 7. Cell 104 — concern sensitivity: remove run_for_k def, call run_sensitivity
# ---------------------------------------------------------------------------
src104 = "".join(cells[104]["source"])

# Remove the def run_for_k(...) block (everything from 'def run_for_k' to the blank line before 'for k in ks:')
src104 = re.sub(
    r'def run_for_k\(k:.*?(?=^for k in ks:)',
    "# run_for_k replaced by run_sensitivity from dialogue_utils (CIP-0002)\n\n",
    src104,
    flags=re.DOTALL | re.MULTILINE,
)

# Replace the for loop call
src104 = src104.replace(
    "    run_for_k(k)",
    "    run_sensitivity(\n"
    "        k, kind='concern',\n"
    "        embeddings_normalized=embeddings_normalized,\n"
    "        df=concerns_df,\n"
    "        output_folder=OUTPUT_FOLDER,\n"
    "        random_seed=RANDOM_SEED,\n"
    "        framing_lens_mappings=FRAMING_LENS_MAPPINGS,\n"
    "    )",
)

set_source(cells[104], src104)

# ---------------------------------------------------------------------------
# 8. Cell 114 — benefit sensitivity: same pattern + fix wrong embeddings var
# ---------------------------------------------------------------------------
src114 = "".join(cells[114]["source"])

# Remove the def run_for_k(...) block
src114 = re.sub(
    r'def run_for_k\(k:.*?(?=^for k in ks:)',
    "# run_for_k replaced by run_sensitivity from dialogue_utils (CIP-0002)\n\n",
    src114,
    flags=re.DOTALL | re.MULTILINE,
)

# Replace the for loop call (also fix: should use benefit_embeddings_normalized, not embeddings_normalized)
src114 = src114.replace(
    "    run_for_k(k)",
    "    run_sensitivity(\n"
    "        k, kind='benefit',\n"
    "        embeddings_normalized=benefit_embeddings_normalized,  # CIP-0002 fix: was erroneously concern embeddings\n"
    "        df=benefits_df,\n"
    "        output_folder=OUTPUT_FOLDER,\n"
    "        random_seed=RANDOM_SEED,\n"
    "        framing_lens_mappings=globals().get('BENEFIT_FRAMING_LENS_MAPPINGS', FRAMING_LENS_MAPPINGS),\n"
    "    )",
)

set_source(cells[114], src114)

# ---------------------------------------------------------------------------
# 9. Save
# ---------------------------------------------------------------------------
with open(OUT_PATH, "w") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Done. Cells modified:")
print("  - Cell 4:  added `from dialogue_utils import *`")
print("  - Cells 5,11,18,24,39,41,63,78,80,92,93,98,99,101,105,108,109,111,115: replaced with comments")
print("  - Cell 14: extract_phrases call (concerns), updated result handling")
print("  - Cell 53: extract_phrases call (benefits), updated result handling")
print("  - Cell 57: removed inline get_embeddings_batch guard")
print("  - Cell 104: run_sensitivity call (concerns)")
print("  - Cell 114: run_sensitivity call (benefits) + fixed embeddings variable")
print("  - ALL:  outputs stripped")
