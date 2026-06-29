#!/usr/bin/env python
"""Create a Scispark workspace skeleton."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "scispark-topic"


STAGE_FILES = [
    "01_fact_extraction.md",
    "02_hypothesis.md",
    "03_initial_idea.md",
    "04_technical_optimization.md",
    "05_moa_optimization.md",
    "06_human_ai_collaboration.md",
]


CSV_HEADER = [
    "id",
    "title",
    "authors",
    "year",
    "venue",
    "doi",
    "arxiv_id",
    "url",
    "pdf_url",
    "source_api",
    "query",
    "stage",
    "usage",
    "verification_status",
    "notes",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("keyword")
    parser.add_argument("--root", default="03-AI笔记/scispark")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    out = Path(args.root) / slugify(args.keyword)
    out.mkdir(parents=True, exist_ok=True)
    (out / "experts").mkdir(exist_ok=True)
    (out / "slides").mkdir(exist_ok=True)

    for name in STAGE_FILES:
        path = out / name
        if args.force or not path.exists():
            path.write_text(f"# {name[:-3]}\n\n", encoding="utf-8")

    csv_path = out / "literature.csv"
    if args.force or not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)

    state = out / "scispark-state.json"
    if args.force or not state.exists():
        state.write_text(
            '{\n  "keyword": "%s",\n  "current_stage": 1,\n  "status": "initialized"\n}\n'
            % args.keyword.replace('"', '\\"'),
            encoding="utf-8",
        )

    print(out.resolve())


if __name__ == "__main__":
    main()
