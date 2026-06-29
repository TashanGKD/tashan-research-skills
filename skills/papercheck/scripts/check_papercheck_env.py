#!/usr/bin/env python
"""Check PaperCheck skill-native runtime without printing secrets."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_REPO = Path(
    os.environ.get("PAPERCHECK_RULES_REPO", str(SKILL_ROOT / "assets" / "paperchecker-rules"))
)
PYTHON_IMPORTS = (
    "docx",
    "fastapi",
    "uvicorn",
    "requests",
    "pymupdf4llm",
)


def exists(path: Path) -> dict:
    return {"path": str(path), "exists": path.exists()}


def import_status(module: str) -> dict:
    return {"module": module, "importable": importlib.util.find_spec(module) is not None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PaperCheck skill-native runtime.")
    parser.add_argument("--rules-repo", type=Path, default=DEFAULT_RULES_REPO)
    args = parser.parse_args()

    rules_repo = args.rules_repo
    required = [
        SKILL_ROOT / "SKILL.md",
        SKILL_ROOT / "scripts" / "extract_citation_evidence.py",
        rules_repo / "README.md",
        rules_repo / "requirements.txt",
        rules_repo / "run_server.py",
        rules_repo / "app" / "main.py",
        rules_repo / "core" / "checker" / "citation_checker.py",
    ]

    report = {
        "skill_root": str(SKILL_ROOT),
        "rules_repo": exists(rules_repo),
        "required_files": [exists(path) for path in required],
        "python_imports": [import_status(module) for module in PYTHON_IMPORTS],
        "python": shutil.which("python") or shutil.which("py") or sys.executable,
        "warnings": [],
        "notes": [
            "No provider API key is required. The mounted Codex model performs semantic review from extracted evidence."
        ],
    }

    missing_imports = [
        item["module"] for item in report["python_imports"] if not item["importable"]
    ]
    if missing_imports:
        report["warnings"].append(
            "Missing Python imports: "
            + ", ".join(missing_imports)
            + ". Install the bundled rules requirements if needed."
        )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    missing = [path for path in required if not path.exists()]
    return 1 if missing or missing_imports else 0


if __name__ == "__main__":
    raise SystemExit(main())
