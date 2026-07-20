#!/usr/bin/env python3
"""Create an auditable host-portable copy of a CriticAgent eval skill."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


def _tree_sha256(root: Path) -> str:
    files = []
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix().casefold(),
    ):
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    encoded = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def adapt_skill(source: Path, target: Path, mapping: dict[str, str]) -> dict[str, Any]:
    """Copy a skill and replace only declared tool assertion names."""
    source = source.resolve()
    target = target.resolve()
    if target.exists():
        raise FileExistsError(f"target already exists: {target}")
    evals_path = source / "evals" / "evals.json"
    if not evals_path.is_file():
        raise FileNotFoundError(f"missing evals/evals.json: {source}")
    if not mapping or any(not key or not value for key, value in mapping.items()):
        raise ValueError("mapping must contain non-empty source and target names")

    source_hash = _tree_sha256(source)
    shutil.copytree(source, target)
    try:
        adapted_path = target / "evals" / "evals.json"
        payload = json.loads(adapted_path.read_text(encoding="utf-8"))
        changes = []
        used = set()
        for case in payload.get("evals", []):
            case_id = str(case.get("id", ""))
            for index, assertion in enumerate(case.get("tool_assertions") or []):
                old_name = assertion.get("name")
                if old_name in mapping:
                    new_name = mapping[old_name]
                    assertion["name"] = new_name
                    used.add(old_name)
                    changes.append(
                        {
                            "case_id": case_id,
                            "assertion_index": index,
                            "from": old_name,
                            "to": new_name,
                        }
                    )
        unused = sorted(set(mapping) - used)
        if unused:
            raise ValueError(f"mapping did not match any assertion names: {unused}")
        adapted_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        adapted_hash = _tree_sha256(target)
        manifest = {
            "schema_version": 1,
            "purpose": "host_tool_name_portability_only",
            "source": str(source),
            "source_tree_sha256": source_hash,
            "adapted_tree_sha256": adapted_hash,
            "mapping": dict(sorted(mapping.items())),
            "changed_assertions": changes,
            "unchanged_contract": [
                "prompts",
                "text assertions",
                "file assertions",
                "fixtures",
                "skill instructions",
            ],
        }
        (target / "host-tool-adaptation.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return manifest
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("target")
    parser.add_argument(
        "--map",
        action="append",
        required=True,
        metavar="SOURCE=TARGET",
        help="replace one exact tool assertion name; may be repeated",
    )
    args = parser.parse_args()
    mapping = {}
    for item in args.map:
        if "=" not in item:
            raise SystemExit(f"ERROR: invalid --map value: {item!r}")
        source_name, target_name = item.split("=", 1)
        mapping[source_name] = target_name
    manifest = adapt_skill(Path(args.source), Path(args.target), mapping)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
