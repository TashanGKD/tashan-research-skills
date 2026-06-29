#!/usr/bin/env python
"""Create a minimal research baseline workspace."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


FILES = {
    "problem_definition.md": "# Problem Definition\n\n## Scientific question\n\n## Research goal\n\n## Input data\n\n## Data description / field meaning\n\n## Expected output\n\n## Unit of analysis\n\n## Data question\n\n## Recommended framework\n\n## Outcome / label / effect\n\n## Features known before output\n\n## Leakage risks\n\n## Missing fields\n",
    "eda_plan.md": "# EDA Plan\n\n- Label/outcome distribution\n- Missingness\n- Feature distributions\n- Group/time/batch/source balance\n- Leakage checks\n",
    "preprocess_plan.md": "# Preprocess Plan\n\n- Cleaning and units\n- Missing values\n- Outliers\n- Encoding\n- Scaling\n- Split protocol\n",
    "baseline_plan.md": "# Baseline Plan\n\n## Sanity baseline\n\n## Interpretable baseline\n\n## Strong classical baseline\n\n## Stronger model only if justified\n",
    "train_eval_plan.md": "# Train and Evaluation Plan\n\n## Split\n\n## Primary metric\n\n## Secondary metrics\n\n## Uncertainty\n\n## Subgroup/error analysis\n",
    "baseline_report.md": "# Baseline Report\n\n## Original scientific goal\n\n## Data task\n\n## Dataset summary\n\n## Framework used\n\n## Models or analyses tested\n\n## Results\n\n## Error analysis\n\n## Scientific interpretation\n\n## Does this answer the goal?\n\n## Next step\n",
}


SCHEMA_HEADER = [
    "field",
    "role",
    "type",
    "required",
    "known_before_outcome",
    "notes",
]


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text, flags=re.UNICODE)
    return re.sub(r"-+", "-", text).strip("-") or "research-baseline"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("topic")
    parser.add_argument("--root", default="03-AI笔记/research-baseline")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    out = Path(args.root) / slugify(args.topic)
    out.mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(exist_ok=True)
    (out / "scripts").mkdir(exist_ok=True)

    for name, content in FILES.items():
        path = out / name
        if args.force or not path.exists():
            path.write_text(content, encoding="utf-8")

    schema = out / "data_schema.csv"
    if args.force or not schema.exists():
        with schema.open("w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(SCHEMA_HEADER)

    print(out.resolve())


if __name__ == "__main__":
    main()
