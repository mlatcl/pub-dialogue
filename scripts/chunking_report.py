"""
Pre-flight chunking report — run BEFORE paying for LLM extraction.

Chunks every PDF twice — with the v19 rule (min_text_coverage=0) and with the
current coverage-based rule — and writes a per-document comparison so you can
check chunk counts, text coverage and image-only flags before running
01_processing.  Makes no API calls.

Usage (from the repo root):
    python scripts/chunking_report.py                       # data/*.pdf
    python scripts/chunking_report.py --pdfs data --ocr     # also OCR scans
    python scripts/chunking_report.py --coverage 0.4 0.5 0.6  # threshold sweep

Output: outputs/chunking_report.csv (+ a printed summary).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run without pip install -e
from pub_dialogue import access  # noqa: E402


def _run(pdfs, **kw) -> pd.DataFrame:
    access.reset_chunk_stats()
    for p in pdfs:
        access.extract_chunks_from_pdf(p, {}, **kw)
    return access.get_doc_diagnostics()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdfs", default="data", help="folder of PDFs (default: data)")
    ap.add_argument("--out", default="outputs/chunking_report.csv")
    ap.add_argument("--coverage", type=float, nargs="+",
                    default=[access.MIN_TEXT_COVERAGE],
                    help="min_text_coverage value(s) to test")
    ap.add_argument("--ocr", action="store_true", help="OCR image-only PDFs")
    ap.add_argument("--min-chunks", type=int, default=20,
                    help="flag documents with fewer chunks than this")
    args = ap.parse_args()

    pdfs = sorted(Path(args.pdfs).glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {Path(args.pdfs).resolve()}")

    old = _run(pdfs, min_text_coverage=0.0)
    cols = ["source_file", "pages", "total_words", "words_per_page",
            "likely_image_only", "blocks_coverage", "newline_coverage"]
    report = old[cols].copy()
    report["v19_segmentation"] = old["segmentation"]
    report["v19_chunks"] = old["chunks_kept"]
    report["v19_coverage"] = old["final_coverage"]

    for cov in args.coverage:
        new = _run(pdfs, min_text_coverage=cov, ocr_if_image_only=args.ocr)
        tag = f"cov{cov:g}"
        report[f"{tag}_segmentation"] = new["segmentation"].values
        report[f"{tag}_reason"] = new["fallback_reason"].values
        report[f"{tag}_chunks"] = new["chunks_kept"].values
        report[f"{tag}_coverage"] = new["final_coverage"].values
        report[f"{tag}_ocr"] = new["ocr_applied"].values

    main_tag = f"cov{args.coverage[0]:g}"
    report["changed"] = report["v19_chunks"] != report[f"{main_tag}_chunks"]
    report["flag"] = (
        report["likely_image_only"]
        | (report[f"{main_tag}_coverage"] < args.coverage[0])
        | (report[f"{main_tag}_chunks"] < args.min_chunks)
    )
    report = report.sort_values(f"{main_tag}_chunks")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.out, index=False)

    pd.set_option("display.width", 200)
    show = ["source_file", "pages", "words_per_page", "v19_chunks", "v19_coverage",
            f"{main_tag}_chunks", f"{main_tag}_coverage", f"{main_tag}_reason"]
    print(f"\n{len(pdfs)} PDFs | v19 chunks: {report['v19_chunks'].sum():,} | "
          f"{main_tag} chunks: {report[f'{main_tag}_chunks'].sum():,}")
    print(f"Documents whose chunking changed: {int(report['changed'].sum())}")
    print("\nChanged documents:")
    print(report.loc[report["changed"], show].to_string(index=False) or "  (none)")
    print("\nStill flagged (image-only, low coverage, or few chunks):")
    print(report.loc[report["flag"], show + ["likely_image_only"]].to_string(index=False)
          or "  (none)")
    if len(args.coverage) > 1:
        print("\nThreshold sweep — total chunks and documents falling back:")
        for cov in args.coverage:
            t = f"cov{cov:g}"
            print(f"  {cov:.2f}: {report[f'{t}_chunks'].sum():,} chunks, "
                  f"{int((report[f'{t}_reason'] == 'low_coverage').sum())} low-coverage fallbacks")
    print(f"\nWritten: {args.out}")


if __name__ == "__main__":
    main()
