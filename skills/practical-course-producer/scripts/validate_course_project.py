from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


GATES = ("plan", "record", "render", "release")
PLAN_ARTIFACTS = ("lesson_plan", "interaction_plan", "recording_checklist", "narration")
REQUIRED_ARTIFACTS = PLAN_ARTIFACTS + ("scene_plan", "final_video", "run_manifest", "audit")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read project file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("course project root must be a JSON object")
    return value


def project_path(root: Path, value: Any, field: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty relative path")
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        errors.append(f"{field} must be relative: {value}")
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        errors.append(f"{field} leaves the project directory: {value}")
        return None
    return resolved


def require_file(root: Path, artifacts: dict[str, Any], key: str, errors: list[str]) -> Path | None:
    value = artifacts.get(key)
    path = project_path(root, value, f"artifacts.{key}", errors)
    if path is None:
        return None
    if not path.is_file():
        errors.append(f"artifacts.{key} does not exist: {value}")
        return None
    if path.stat().st_size == 0:
        errors.append(f"artifacts.{key} is empty: {value}")
        return None
    return path


def validate_metadata(project: dict[str, Any], errors: list[str]) -> dict[str, Any] | None:
    if project.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    for field in ("slug", "topic", "audience", "language", "aspect_ratio"):
        if not isinstance(project.get(field), str) or not project[field].strip():
            errors.append(f"{field} must be a non-empty string")
    duration = project.get("target_duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        errors.append("target_duration_seconds must be a positive number")
    artifacts = project.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be a JSON object")
        return None
    for key in REQUIRED_ARTIFACTS:
        if key not in artifacts:
            errors.append(f"artifacts.{key} is required")
    return artifacts


def validate_scene_sources(root: Path, scene_plan_path: Path, errors: list[str]) -> None:
    try:
        scene_plan = json.loads(scene_plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"artifacts.scene_plan is not valid JSON: {exc}")
        return
    scenes = scene_plan.get("scenes") if isinstance(scene_plan, dict) else None
    if not isinstance(scenes, list) or not scenes:
        errors.append("artifacts.scene_plan must contain a non-empty scenes array")
        return
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            errors.append(f"scene {index} must be a JSON object")
            continue
        scene_id = scene.get("id") if isinstance(scene.get("id"), str) else str(index)
        source_value = scene.get("source")
        source = project_path(scene_plan_path.parent, source_value, f"scene {scene_id} source", errors)
        if source is None:
            continue
        try:
            source.relative_to(root)
        except ValueError:
            errors.append(f"scene {scene_id} source leaves the project directory: {source_value}")
            continue
        if not source.is_file():
            errors.append(f"scene {scene_id} source does not exist: {source_value}")
        elif source.stat().st_size == 0:
            errors.append(f"scene {scene_id} source is empty: {source_value}")


def validate_project(project_path_value: Path, gate: str) -> dict[str, Any]:
    project_path_value = project_path_value.resolve()
    root = project_path_value.parent
    project = read_json(project_path_value)
    errors: list[str] = []
    artifacts = validate_metadata(project, errors)

    if artifacts is not None:
        for key in PLAN_ARTIFACTS:
            require_file(root, artifacts, key, errors)

        if GATES.index(gate) >= GATES.index("record"):
            scene_plan = require_file(root, artifacts, "scene_plan", errors)
            if scene_plan is not None:
                validate_scene_sources(root, scene_plan, errors)

        if GATES.index(gate) >= GATES.index("render"):
            require_file(root, artifacts, "final_video", errors)
            run_manifest = require_file(root, artifacts, "run_manifest", errors)
            if run_manifest is not None:
                try:
                    json.loads(run_manifest.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    errors.append(f"artifacts.run_manifest is not valid JSON: {exc}")

        if gate == "release":
            require_file(root, artifacts, "audit", errors)

    return {
        "schema_version": 1,
        "project": project_path_value.name,
        "gate": gate,
        "status": "pass" if not errors else "fail",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether a practical-course project can enter a production gate.")
    parser.add_argument("project", type=Path, help="Path to course-project.json")
    parser.add_argument("--gate", choices=GATES, required=True)
    args = parser.parse_args()
    try:
        result = validate_project(args.project, args.gate)
    except ValueError as exc:
        result = {
            "schema_version": 1,
            "project": args.project.name,
            "gate": args.gate,
            "status": "fail",
            "errors": [str(exc)],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
