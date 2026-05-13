"""Add AI-generated prose descriptions to split notebooks.

For each code cell that lacks a preceding markdown cell, calls an LLM to write
a 2-3 sentence description and inserts it as a new markdown cell immediately
before the code cell.

Usage
-----
# Dry run — print descriptions without modifying notebooks
python scripts/add_notebook_descriptions.py --dry-run

# Apply to all target notebooks
python scripts/add_notebook_descriptions.py

# Apply to a single notebook
python scripts/add_notebook_descriptions.py --notebook 03_ai_distinctiveness.ipynb

# Use a stronger model
python scripts/add_notebook_descriptions.py --model gpt-4o
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Notebook names and their plain-English purpose summaries
# ---------------------------------------------------------------------------

NOTEBOOK_PURPOSES: dict[str, str] = {
    "00_data_quality.ipynb": (
        "Data quality assessment of extracted paragraph-level text from "
        "65 UK public dialogue PDF documents on science and technology."
    ),
    "01_processing.ipynb": (
        "End-to-end pipeline: PDF ingestion, concern and benefit phrase extraction "
        "via LLM, semantic embedding, and k-means clustering of concern phrases "
        "from 65 UK public dialogue documents."
    ),
    "01a_clustering.ipynb": (
        "Cluster labelling and k-sensitivity robustness analysis for concern and "
        "benefit phrase embeddings produced by 01_processing.ipynb."
    ),
    "02_shared_structure.ipynb": (
        "Analysis of shared concern and benefit structure across all technologies "
        "in 65 UK public dialogue documents, including cross-cutting themes and "
        "document-weighted framing lens profiles."
    ),
    "03_ai_distinctiveness.ipynb": (
        "Identifying what makes AI-related public dialogues distinctive: "
        "comparing AI versus non-AI dialogues on concern framings, benefit framings, "
        "and cross-cutting themes."
    ),
    "04_temporal_dynamics.ipynb": (
        "Temporal dynamics of AI-specific concerns and benefits across public "
        "dialogues from different time periods, using a sliding-window approach."
    ),
    "05_robustness.ipynb": (
        "Robustness checks: sensitivity of the main findings to embedding model "
        "choice, clustering granularity (k), and extraction prompt variations."
    ),
}

TARGET_NOTEBOOKS = list(NOTEBOOK_PURPOSES.keys())

SYSTEM_PROMPT = (
    "You are a scientific notebook annotator. "
    "Write a concise 2-3 sentence markdown description (plain prose, no heading) "
    "explaining what the following notebook cell does and why it matters in the "
    "overall analysis. "
    "Write for a reader familiar with NLP and public dialogue research. "
    "Do not repeat the cell title verbatim. "
    "Do not use bullet points or sub-headings — prose only."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_title(source: str) -> str:
    """Return the first `# @title` value found in a cell's source, or ''."""
    for line in source.splitlines():
        m = re.match(r"#\s*@title\s+(.*)", line)
        if m:
            return m.group(1).strip()
    return ""


def _nearest_section_heading(cells: list[dict], cell_idx: int) -> str:
    """Return the text of the nearest preceding markdown heading, or ''."""
    for i in range(cell_idx - 1, -1, -1):
        if cells[i]["cell_type"] == "markdown":
            src = "".join(cells[i]["source"]).strip()
            # Return first non-empty heading line
            for line in src.splitlines():
                if line.startswith("#"):
                    return line.lstrip("#").strip()
            return src[:120]
    return ""


def _has_preceding_markdown(cells: list[dict], cell_idx: int) -> bool:
    """Return True if the cell immediately before cell_idx is markdown."""
    if cell_idx == 0:
        return False
    return cells[cell_idx - 1]["cell_type"] == "markdown"


def _make_markdown_cell(text: str) -> dict:
    """Build a notebook markdown cell dict from a text string."""
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        pass  # last line has no trailing newline — that's fine for nbformat
    return {
        "cell_type": "markdown",
        "id": _new_cell_id(),
        "metadata": {},
        "source": lines if lines else [text],
    }


_cell_id_counter = 0


def _new_cell_id() -> str:
    global _cell_id_counter
    _cell_id_counter += 1
    return f"generated-desc-{_cell_id_counter:04d}"


def _build_user_prompt(
    notebook_name: str,
    section: str,
    title: str,
    source: str,
) -> str:
    parts = [f"Notebook: {notebook_name}"]
    if section:
        parts.append(f"Section: {section}")
    if title:
        parts.append(f"Cell title: {title}")
    parts.append(f"Code:\n```python\n{source}\n```")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def generate_description(
    client,
    notebook_name: str,
    notebook_purpose: str,
    section: str,
    title: str,
    source: str,
) -> str:
    """Call the LLM and return a prose description string."""
    system = SYSTEM_PROMPT + f"\n\nNotebook purpose: {notebook_purpose}"
    user = _build_user_prompt(notebook_name, section, title, source)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return client.complete(messages, temperature=0.3, max_tokens=200)


def process_notebook(
    nb_path: Path,
    client,
    dry_run: bool = False,
    verbose: bool = True,
) -> int:
    """Process one notebook. Returns the number of cells inserted."""
    purpose = NOTEBOOK_PURPOSES.get(nb_path.name, "")
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    cells: list[dict] = nb["cells"]

    insertions: list[tuple[int, str]] = []  # (original_index, description_text)

    for idx, cell in enumerate(cells):
        if cell["cell_type"] != "code":
            continue
        if _has_preceding_markdown(cells, idx):
            continue

        source = "".join(cell["source"])
        if not source.strip():
            continue  # skip empty cells

        title = _extract_title(source)
        section = _nearest_section_heading(cells, idx)

        if verbose:
            label = title or source[:60].replace("\n", " ")
            print(f"  [{nb_path.name}] cell {idx}: {label!r}")

        description = generate_description(
            client=client,
            notebook_name=nb_path.name,
            notebook_purpose=purpose,
            section=section,
            title=title,
            source=source,
        )

        if verbose or dry_run:
            print(f"    → {description[:120]}{'...' if len(description) > 120 else ''}")

        insertions.append((idx, description))

    if dry_run:
        print(f"  [dry-run] would insert {len(insertions)} markdown cells into {nb_path.name}")
        return len(insertions)

    # Apply insertions in reverse order so indices stay valid
    for original_idx, description in reversed(insertions):
        md_cell = _make_markdown_cell(description)
        cells.insert(original_idx, md_cell)

    nb["cells"] = cells
    nb_path.write_text(
        json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"  Inserted {len(insertions)} description cells into {nb_path.name}")
    return len(insertions)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Add AI-generated descriptions to split notebooks."
    )
    p.add_argument(
        "--notebook",
        metavar="FILENAME",
        help="Process only this notebook (filename only, e.g. 03_ai_distinctiveness.ipynb). "
             "Defaults to all target notebooks.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print descriptions without modifying any notebooks.",
    )
    p.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="LiteLLM model string (default: gpt-4o-mini).",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-cell output; only print summary lines.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    # Determine which notebooks to process
    repo_root = Path(__file__).parent.parent

    # Load .env so OPENAI_API_KEY / ANTHROPIC_API_KEY are available
    try:
        from dotenv import load_dotenv
        load_dotenv(repo_root / ".env")
    except ImportError:
        pass  # python-dotenv not installed; rely on environment variables
    if args.notebook:
        targets = [repo_root / args.notebook]
    else:
        targets = [repo_root / name for name in TARGET_NOTEBOOKS]

    missing = [t for t in targets if not t.exists()]
    if missing:
        print("ERROR: notebook(s) not found:", [str(m) for m in missing], file=sys.stderr)
        sys.exit(1)

    # Import LLMClient (lazy so the module loads even without litellm installed)
    sys.path.insert(0, str(repo_root))
    from pub_dialogue.client import LLMClient

    client = LLMClient(model=args.model)
    verbose = not args.quiet

    total_inserted = 0
    for nb_path in targets:
        if verbose:
            print(f"\n=== {nb_path.name} ===")
        count = process_notebook(
            nb_path=nb_path,
            client=client,
            dry_run=args.dry_run,
            verbose=verbose,
        )
        total_inserted += count

    action = "would insert" if args.dry_run else "inserted"
    print(f"\nDone. Total description cells {action}: {total_inserted}")


if __name__ == "__main__":
    main()
