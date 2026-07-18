from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

from advance_course_project import advance  # noqa: E402
from build_course_video import require_tool, run  # noqa: E402


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = SKILL_ROOT / "tests" / "fixtures" / "course-project"


def fingerprint(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def create_recording(ffmpeg: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=30:duration=0.8",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=0.8",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(destination),
        ]
    )


def require_pass(code: int, payload: dict[str, Any], stage: str) -> None:
    if code != 0 or payload.get("status") != "pass":
        raise RuntimeError(f"{stage} failed: {payload.get('errors', payload)}")


def smoke() -> dict[str, Any]:
    before = fingerprint(SKILL_ROOT)
    ffmpeg = require_tool("ffmpeg")
    require_tool("ffprobe")

    with tempfile.TemporaryDirectory(prefix="public-course-project-") as temp_value:
        project_root = Path(temp_value) / "course-project"
        shutil.copytree(FIXTURE, project_root)
        project_path = project_root / "course-project.json"
        create_recording(ffmpeg, project_root / "recordings" / "demo.mp4")

        record_code, record_payload = advance(project_path, "record")
        require_pass(record_code, record_payload, "record")
        render_code, render_payload = advance(project_path, "render")
        require_pass(render_code, render_payload, "render")
        release_code, release_payload = advance(project_path, "release")
        require_pass(release_code, release_payload, "release")

        project = json.loads(project_path.read_text(encoding="utf-8"))
        artifacts = project["artifacts"]
        video = project_root / artifacts["final_video"]
        manifest = project_root / artifacts["run_manifest"]
        audit = project_root / artifacts["audit"]
        frames = sorted((project_root / "audit-frames").glob("frame-*.png"))
        if not video.is_file() or not manifest.is_file() or not audit.is_file() or len(frames) != 3:
            raise RuntimeError("smoke output is incomplete")

        result = {
            "schema_version": 1,
            "status": "pass",
            "final_gate": release_payload["gate"],
            "video": artifacts["final_video"],
            "run_manifest": artifacts["run_manifest"],
            "audit": artifacts["audit"],
            "representative_frames": len(frames),
            "sha256": release_payload["sha256"],
        }

    result["checkout_unchanged"] = fingerprint(SKILL_ROOT) == before
    if not result["checkout_unchanged"]:
        raise RuntimeError("smoke run modified the skill checkout")
    return result


def main() -> int:
    try:
        payload = smoke()
        code = 0
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        payload = {"schema_version": 1, "status": "fail", "errors": [str(exc)]}
        code = 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
