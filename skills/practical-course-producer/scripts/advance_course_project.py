from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from audit_course_project import audit_project
from build_course_video import build
from validate_course_project import GATES, read_json, validate_project


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def blocked(result: dict[str, Any], gate: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "fail",
        "blocked_at": gate or result["gate"],
        "errors": result["errors"],
    }


def relative_project_path(root: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty relative path")
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError(f"{field} must be relative: {value}")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{field} leaves the project directory: {value}") from exc
    return resolved


def write_project(path: Path, project: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def validate_only(project_path: Path, gate: str) -> tuple[int, dict[str, Any]]:
    result = validate_project(project_path, gate)
    if result["status"] != "pass":
        return 2, blocked(result)
    return 0, {
        "schema_version": 1,
        "status": "pass",
        "gate": gate,
        "project": project_path.name,
    }


def render(project_path: Path) -> tuple[int, dict[str, Any]]:
    record_result = validate_project(project_path, "record")
    if record_result["status"] != "pass":
        return 2, blocked(record_result, "record")

    root = project_path.parent
    project = read_json(project_path)
    artifacts = project["artifacts"]
    scene_plan = relative_project_path(root, artifacts["scene_plan"], "artifacts.scene_plan")
    pending_video = relative_project_path(root, artifacts["final_video"], "artifacts.final_video")

    try:
        video, manifest = build(scene_plan, pending_video.parent)
    except (OSError, RuntimeError, ValueError) as exc:
        return 2, {
            "schema_version": 1,
            "status": "fail",
            "blocked_at": "render",
            "errors": [str(exc)],
        }

    artifacts["final_video"] = video.relative_to(root).as_posix()
    artifacts["run_manifest"] = manifest.relative_to(root).as_posix()
    write_project(project_path, project)

    render_result = validate_project(project_path, "render")
    if render_result["status"] != "pass":
        return 2, blocked(render_result, "render")
    return 0, {
        "schema_version": 1,
        "status": "pass",
        "gate": "render",
        "project": project_path.name,
        "video": artifacts["final_video"],
        "run_manifest": artifacts["run_manifest"],
    }


def advance(project_path: Path, target: str) -> tuple[int, dict[str, Any]]:
    project_path = project_path.resolve()
    if target == "release":
        return audit_project(project_path)
    if target in {"plan", "record"}:
        return validate_only(project_path, target)
    return render(project_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Advance a practical-course project through verified production gates.")
    parser.add_argument("project", type=Path, help="Path to course-project.json")
    parser.add_argument("--to", choices=GATES, required=True, dest="target")
    args = parser.parse_args()
    try:
        code, payload = advance(args.project, args.target)
    except (OSError, ValueError, KeyError) as exc:
        code = 2
        payload = {
            "schema_version": 1,
            "status": "fail",
            "blocked_at": args.target,
            "errors": [str(exc)],
        }
    emit(payload)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
