from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from build_course_video import probe_media, require_tool, run
from validate_course_project import read_json, validate_project


SILENCE_END = re.compile(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)")
DURATION_TOLERANCE = 0.20


def relative_path(root: Path, value: Any, field: str) -> Path:
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def tool_version(executable: str) -> str:
    result = run([executable, "-version"])
    return result.stdout.splitlines()[0].strip()


def silence_intervals(ffmpeg: str, video: Path) -> list[dict[str, float]]:
    result = run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-i",
            str(video),
            "-af",
            "silencedetect=noise=-40dB:d=1.5",
            "-f",
            "null",
            os.devnull,
        ]
    )
    intervals = []
    for match in SILENCE_END.finditer(result.stderr):
        end = float(match.group(1))
        duration = float(match.group(2))
        intervals.append({"start": max(0.0, end - duration), "end": end, "duration": duration})
    return intervals


def extract_frames(ffmpeg: str, video: Path, duration: float, directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    frames = []
    for index, fraction in enumerate((0.1, 0.5, 0.9), start=1):
        destination = directory / f"frame-{index:02d}.png"
        run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-y",
                "-ss",
                f"{duration * fraction:.6f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                str(destination),
            ]
        )
        if not destination.is_file() or destination.stat().st_size == 0:
            raise RuntimeError(f"representative frame was not created: {destination.name}")
        frames.append(destination)
    return frames


def write_report(
    path: Path,
    video_ref: str,
    digest: str,
    duration: float,
    probe: dict[str, Any],
    intervals: list[dict[str, float]],
    frame_refs: list[str],
    ffmpeg_version: str,
    ffprobe_version: str,
) -> None:
    streams = probe.get("streams", [])
    video_stream = next(stream for stream in streams if stream.get("codec_type") == "video")
    audio_stream = next(stream for stream in streams if stream.get("codec_type") == "audio")
    silence_lines = [
        f"- {item['start']:.3f}s to {item['end']:.3f}s ({item['duration']:.3f}s)" for item in intervals
    ] or ["- None at -40 dB for 1.5 seconds or longer"]
    frame_lines = [f"- `{ref}`" for ref in frame_refs]
    report = [
        "# Course Media Audit",
        "",
        "Automated media integrity: PASS",
        "",
        "## Artifact",
        "",
        f"- Video: `{video_ref}`",
        f"- SHA-256: `{digest}`",
        f"- Duration: {duration:.6f} seconds",
        f"- Video: {video_stream.get('width')}x{video_stream.get('height')} at {video_stream.get('r_frame_rate')}",
        f"- Audio: {audio_stream.get('sample_rate')} Hz, {audio_stream.get('channels')} channels",
        "",
        "## Toolchain",
        "",
        f"- {ffmpeg_version}",
        f"- {ffprobe_version}",
        "",
        "## Silence intervals",
        "",
        *silence_lines,
        "",
        "## Representative frames",
        "",
        *frame_lines,
        "",
        "## Review boundary",
        "",
        "This report verifies media structure and extracts review evidence. Human review must still confirm teaching accuracy, readability, and narration alignment.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text("\n".join(report), encoding="utf-8")
    os.replace(temporary, path)


def audit_project(project_path: Path) -> tuple[int, dict[str, Any]]:
    project_path = project_path.resolve()
    render_result = validate_project(project_path, "render")
    if render_result["status"] != "pass":
        return 2, {"schema_version": 1, "status": "fail", "blocked_at": "render", "errors": render_result["errors"]}

    root = project_path.parent
    project = read_json(project_path)
    artifacts = project["artifacts"]
    video = relative_path(root, artifacts["final_video"], "artifacts.final_video")
    audit = relative_path(root, artifacts["audit"], "artifacts.audit")
    ffmpeg = require_tool("ffmpeg")
    ffprobe = require_tool("ffprobe")
    probe = probe_media(ffprobe, video)
    streams = probe.get("streams", [])
    if not any(stream.get("codec_type") == "video" for stream in streams):
        raise ValueError("final video has no video stream")
    if not any(stream.get("codec_type") == "audio" for stream in streams):
        raise ValueError("final video has no audio stream")
    duration = float(probe["format"]["duration"])
    if duration <= 0:
        raise ValueError("final video duration must be positive")
    target_duration = float(project["target_duration_seconds"])
    minimum_duration = target_duration * (1 - DURATION_TOLERANCE)
    maximum_duration = target_duration * (1 + DURATION_TOLERANCE)
    if not minimum_duration <= duration <= maximum_duration:
        raise ValueError(
            f"final video duration {duration:.3f}s is outside target duration range "
            f"{minimum_duration:.3f}s-{maximum_duration:.3f}s"
        )

    frames = extract_frames(ffmpeg, video, duration, root / "audit-frames")
    frame_refs = [frame.relative_to(root).as_posix() for frame in frames]
    digest = sha256(video)
    intervals = silence_intervals(ffmpeg, video)
    write_report(
        audit,
        artifacts["final_video"],
        digest,
        duration,
        probe,
        intervals,
        frame_refs,
        tool_version(ffmpeg),
        tool_version(ffprobe),
    )
    release_result = validate_project(project_path, "release")
    if release_result["status"] != "pass":
        return 2, {"schema_version": 1, "status": "fail", "blocked_at": "release", "errors": release_result["errors"]}
    return 0, {
        "schema_version": 1,
        "status": "pass",
        "gate": "release",
        "project": project_path.name,
        "audit": artifacts["audit"],
        "sha256": digest,
        "frames": frame_refs,
        "silence_intervals": intervals,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create deterministic media evidence for a rendered course project.")
    parser.add_argument("project", type=Path, help="Path to course-project.json")
    args = parser.parse_args()
    try:
        code, payload = audit_project(args.project)
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        code = 2
        payload = {"schema_version": 1, "status": "fail", "blocked_at": "release", "errors": [str(exc)]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
