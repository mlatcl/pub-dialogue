"""
Pre-flight chunking report — run BEFORE paying for LLM extraction.

Segments every PDF with lynguine ``pub_dialogue.v1`` (CIP-0015) and writes a
per-document summary so you can check chunk counts and sparse-text flags before
running 01_processing.  Makes no API calls.

Usage (from the repo root):
    python scripts/chunking_report.py                       # data/*.pdf
    python scripts/chunking_report.py --pdfs data
    python scripts/chunking_report.py --filter-chrome       # cleaner chrome

Output: outputs/chunking_report.csv (+ a printed summary).
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run without pip install -e
from lynguine.access.documents import (  # noqa: E402
    document_features,
    read_pdf,
    segment_pdf_frame,
)
from pub_dialogue import access  # noqa: E402


def _segment_one(pdf: Path, stage: access.AccessStage) -> dict:
    root = str(pdf.parent.resolve())
    kw = stage.segment_kwargs()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        units = segment_pdf_frame(
            str(pdf),
            allowed_roots=[root],
            **kw,
        )
    sparse_warn = any("text_layer" in str(w.message) for w in caught)

    feats: dict = {}
    try:
        doc = read_pdf(str(pdf), allowed_roots=[root])
        feats = document_features(doc)
        text_layer = getattr(doc.text_layer, "value", str(doc.text_layer))
        pages = len(doc.pages)
        words_per_page = float(doc.words_per_page)
        total_words = int(getattr(doc, "total_words", 0) or 0)
    except Exception as exc:
        text_layer = "error"
        pages = 0
        words_per_page = 0.0
        total_words = 0
        feats = {"error": str(exc)}

    methods = (
        sorted(units["chunking_method"].dropna().unique().tolist())
        if len(units) and "chunking_method" in units.columns
        else []
    )
    segmentation = (
        units["segmentation"].iloc[0]
        if len(units) and "segmentation" in units.columns
        else None
    )
    return {
        "source_file": pdf.name,
        "pages": pages,
        "total_words": total_words or int(feats.get("total_words") or 0),
        "words_per_page": round(words_per_page or float(feats.get("words_per_page") or 0), 1),
        "text_layer": text_layer,
        "sparse_warning": sparse_warn,
        "chunks_kept": len(units),
        "words_kept": int(units["word_count"].sum()) if len(units) else 0,
        "segmentation": segmentation,
        "methods": ",".join(methods),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--pdfs", default="data", help="folder of PDFs (default: data)")
    ap.add_argument("--out", default="outputs/chunking_report.csv")
    ap.add_argument(
        "--filter-chrome",
        action="store_true",
        help="pass filter_chrome=True to lynguine (default: False for parity)",
    )
    ap.add_argument(
        "--min-chunks",
        type=int,
        default=20,
        help="flag documents with fewer chunks than this",
    )
    ap.add_argument(
        "--on-sparse-text",
        default=None,
        choices=["warn", "error", "empty"],
        help="override AccessStage.on_sparse_text",
    )
    args = ap.parse_args()

    pdfs = sorted(Path(args.pdfs).glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {Path(args.pdfs).resolve()}")

    stage = access.AccessStage(filter_chrome=args.filter_chrome)
    if args.on_sparse_text is not None:
        stage.on_sparse_text = args.on_sparse_text

    rows = [_segment_one(p, stage) for p in pdfs]
    report = pd.DataFrame(rows)
    report["flag"] = (report["chunks_kept"] < args.min_chunks) | report[
        "sparse_warning"
    ] | (report["text_layer"].isin(["absent", "sparse"]))
    report = report.sort_values("chunks_kept")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.out, index=False)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    print(report.to_string(index=False))
    print()
    print(f"Wrote {args.out} ({len(report)} documents, "
          f"{int(report['flag'].sum())} flagged)")


if __name__ == "__main__":
    main()
