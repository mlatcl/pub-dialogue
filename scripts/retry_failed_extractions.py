"""
scripts/retry_failed_extractions.py — Retry failed LLM extraction chunks.

Reads the error CSV written by the extraction cells in 01_processing.ipynb,
identifies chunks that failed (e.g. due to rate limiting) and still have no
results in the cache, re-extracts them with exponential-backoff retry, and
writes the updated cache and output CSV.

Usage
-----
    # Retry both tracks (default)
    python scripts/retry_failed_extractions.py

    # Retry only one track
    python scripts/retry_failed_extractions.py --kind concern
    python scripts/retry_failed_extractions.py --kind benefit

    # Dry run — show how many chunks need retrying, don't call the API
    python scripts/retry_failed_extractions.py --dry-run

    # Override the model (default: gpt-4o-mini)
    python scripts/retry_failed_extractions.py --model gpt-4o-mini

Environment
-----------
Requires OPENAI_API_KEY (or the appropriate key for your model) to be set,
or a .env file in the repo root.  Uses the same LLMClient used by the notebook.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Repo-root resolution
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = REPO_ROOT / "outputs"
CHECKPOINTS = REPO_ROOT / "checkpoints"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logger = logging.getLogger("retry_extractions")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env")
        logger.debug("Loaded .env from %s", REPO_ROOT)
    except ImportError:
        pass


def _failed_ids(kind: str) -> set[str]:
    """Return chunk IDs that errored on the previous run."""
    err_path = OUTPUTS / f"extraction_errors_{kind}.csv"
    if not err_path.exists() or err_path.stat().st_size == 0:
        logger.info("No error CSV found at %s — nothing to retry.", err_path)
        return set()
    try:
        df = pd.read_csv(err_path)
    except pd.errors.EmptyDataError:
        logger.info("Error CSV at %s is empty — nothing to retry.", err_path)
        return set()
    if df.empty:
        logger.info("No failures recorded in %s.", err_path.name)
        return set()
    ids = set(df["chunk_id"].tolist())
    logger.info("Found %d previously-failed chunk IDs in %s", len(ids), err_path.name)
    return ids


def _stale_ids(kind: str, cache: dict, failed: set[str]) -> set[str]:
    """Return the subset of failed IDs that still have zero results in cache."""
    key = f"{kind}s"  # "concerns" / "benefits"
    stale = {cid for cid in failed
             if cid in cache and len(cache[cid].get(key, [])) == 0}
    logger.info("%d of those still have zero %s in cache — will retry.", len(stale), key)
    return stale


def _retry_kind(
    kind: str,
    chunks_df: pd.DataFrame,
    client,
    dry_run: bool,
    max_workers: int,
) -> None:
    """Retry all stale failed chunks for one extraction track."""
    import pub_dialogue.utils as du

    cache_file = CHECKPOINTS / f"extracted_{kind}s.json"
    output_csv = OUTPUTS / f"extracted_{kind}s.csv"

    # Load existing cache
    if not cache_file.exists():
        logger.error("Cache file not found: %s — run the notebook first.", cache_file)
        return
    with open(cache_file) as f:
        cache = json.load(f)

    failed = _failed_ids(kind)
    if not failed:
        return

    stale = _stale_ids(kind, cache, failed)
    if not stale:
        logger.info("All previously-failed %s chunks now have results — nothing to do.", kind)
        return

    if dry_run:
        logger.info("[DRY RUN] Would retry %d %s chunks.", len(stale), kind)
        return

    rows_to_run = [(i, row) for i, row in chunks_df.iterrows()
                   if row["chunk_id"] in stale]
    missing = stale - set(chunks_df["chunk_id"])
    if missing:
        logger.warning("%d stale chunk IDs not found in paragraph_chunks.csv: %s",
                       len(missing), sorted(missing)[:5])

    logger.info("Retrying %d %s chunks with %d workers...", len(rows_to_run), kind, max_workers)

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(du.extract_phrases, row, kind, client): row[1]["chunk_id"]
            for row in rows_to_run
        }
        for future in tqdm(as_completed(futures), total=len(futures),
                           desc=f"Retrying {kind}s"):
            result = future.result()
            results.append(result)
            meta_row = chunks_df.loc[chunks_df["chunk_id"] == result.chunk_id].iloc[0]
            cache[result.chunk_id] = {
                f"{kind}s": result.retained_phrases,
                "technology": meta_row["technology"],
                "year": int(meta_row["year"]) if pd.notna(meta_row["year"]) else None,
                "source_file": meta_row["source_file"],
            }

    # Persist updated cache
    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=2)
    logger.info("Cache updated: %s", cache_file)

    # Write updated diagnostics
    du.write_extraction_diagnostics(results, kind, OUTPUTS)

    # Summarise
    still_failed = [r for r in results if r.error]
    logger.info(
        "Retry complete: %d/%d succeeded, %d still failing.",
        len(results) - len(still_failed), len(results), len(still_failed),
    )
    if still_failed:
        logger.warning("Still failing after retry: %s",
                       [r.chunk_id for r in still_failed[:10]])

    # Rebuild and write the flat output CSV from the full cache
    key = f"{kind}s"
    rows = [
        {
            "chunk_id": cid,
            kind: phrase,
            "technology": data["technology"],
            "year": data["year"],
            "source_file": data["source_file"],
        }
        for cid, data in cache.items()
        for phrase in data.get(key, [])
    ]
    cols = ["chunk_id", kind, "technology", "year", "source_file"]
    out_df = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)
    out_df[f"{kind}_id"] = [f"{kind}_{i}" for i in range(len(out_df))]
    out_df.to_csv(output_csv, index=False)
    logger.info("Output CSV written: %s  (%d rows)", output_csv, len(out_df))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kind", choices=["concern", "benefit", "both"], default="both",
                        help="Which extraction track to retry (default: both)")
    parser.add_argument("--model", default="gpt-4o-mini",
                        help="LLM model name (default: gpt-4o-mini)")
    parser.add_argument("--workers", type=int, default=5,
                        help="Parallel workers (default: 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be retried without calling the API")
    args = parser.parse_args()

    _load_env()

    # Load chunks
    chunks_csv = OUTPUTS / "paragraph_chunks.csv"
    if not chunks_csv.exists():
        logger.error("paragraph_chunks.csv not found at %s — run 01_processing.ipynb first.", chunks_csv)
        sys.exit(1)
    chunks_df = pd.read_csv(chunks_csv)
    logger.info("Loaded %d chunks from %s", len(chunks_df), chunks_csv.name)

    if not args.dry_run:
        import os
        from pub_dialogue.client import LLMClient
        client = LLMClient(model=args.model)
        logger.info("LLMClient ready — model: %s", args.model)
    else:
        client = None

    kinds = ["concern", "benefit"] if args.kind == "both" else [args.kind]
    for kind in kinds:
        logger.info("=== %s track ===", kind.upper())
        _retry_kind(kind, chunks_df, client, args.dry_run, args.workers)


if __name__ == "__main__":
    main()
