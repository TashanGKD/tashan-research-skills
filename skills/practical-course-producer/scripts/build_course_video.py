#!/usr/bin/env python
"""Build a versioned practical-course video from real source recordings."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read scene plan {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("scene plan root must be a JSON object")
    return data


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic output"
        raise RuntimeError(f"command failed ({result.returncode}): {detail}")
    return result


def require_tool(name: str) -> str:
    resolved = shutil.which(name)
    if not resolved:
        raise RuntimeError(f"required executable is not on PATH: {name}")
    return resolved


def probe_media(ffprobe: str, path: Path) -> dict[str, Any]:
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height,r_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ]
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe returned invalid JSON for {path}") from exc


def finite_number(value: Any, label: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ValueError(f"{label} must be finite and >= {minimum}")
    return result


def positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return slug or "course"


def next_output(output_dir: Path, slug: str) -> Path:
    pattern = re.compile(rf"^{re.escape(slug)}_v(\d{{3}})\.mp4$")
    versions = [
        int(match.group(1))
        for path in output_dir.glob(f"{slug}_v*.mp4")
        if (match := pattern.match(path.name))
    ]
    return output_dir / f"{slug}_v{max(versions, default=0) + 1:03d}.mp4"


def read_captions(path: Path, scene_id: str, duration: float) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read captions for scene {scene_id}: {exc}") from exc
    raw_segments = payload.get("segments") if isinstance(payload, dict) else None
    if not isinstance(raw_segments, list) or not raw_segments:
        raise ValueError(f"scene {scene_id} captions must contain segments")
    segments: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_segments):
        if not isinstance(raw, dict) or not isinstance(raw.get("text"), str) or not raw["text"].strip():
            raise ValueError(f"scene {scene_id} caption {index} must contain text")
        start = finite_number(raw.get("start"), f"scene {scene_id} caption {index} start")
        end = finite_number(raw.get("end"), f"scene {scene_id} caption {index} end", 0.001)
        if end <= start:
            raise ValueError(f"scene {scene_id} caption {index} must end after it starts")
        if end > duration + 0.05:
            raise ValueError(f"scene {scene_id} caption {index} ends after scene duration")
        segments.append({"text": raw["text"].strip(), "start": start, "end": end})
    return segments


def ass_time(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, fraction = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{fraction:02d}"


def write_ass(path: Path, segments: list[dict[str, Any]], settings: dict[str, int]) -> None:
    font_size = max(8, round(settings["height"] * 0.042))
    horizontal_margin = max(12, round(settings["width"] * 0.06))
    vertical_margin = max(10, round(settings["height"] * 0.045))
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {settings['width']}",
        f"PlayResY: {settings['height']}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        (
            f"Style: Default,Microsoft YaHei,{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,"
            f"-1,0,0,0,100,100,0,0,3,1,0,2,{horizontal_margin},{horizontal_margin},{vertical_margin},1"
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for segment in segments:
        text = segment["text"].replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")
        lines.append(
            f"Dialogue: 0,{ass_time(segment['start'])},{ass_time(segment['end'])},Default,,0,0,0,,{text}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def ass_filter_path(path: Path) -> str:
    return path.resolve().as_posix().replace(":", r"\:").replace("'", r"\'")


def validate_plan(plan_path: Path, plan: dict[str, Any], ffprobe: str) -> tuple[dict[str, int], list[dict[str, Any]]]:
    video = plan.get("video", {})
    if not isinstance(video, dict):
        raise ValueError("video must be a JSON object")
    settings = {
        "width": positive_int(video.get("width", 1280), "video.width"),
        "height": positive_int(video.get("height", 720), "video.height"),
        "fps": positive_int(video.get("fps", 30), "video.fps"),
        "sample_rate": positive_int(video.get("sample_rate", 48000), "video.sample_rate"),
    }
    if settings["width"] % 2 or settings["height"] % 2:
        raise ValueError("video.width and video.height must be even for yuv420p output")

    raw_scenes = plan.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise ValueError("scenes must be a non-empty JSON array")

    scenes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_scenes):
        if not isinstance(raw, dict):
            raise ValueError(f"scenes[{index}] must be a JSON object")
        scene_id = raw.get("id")
        if not isinstance(scene_id, str) or not scene_id.strip():
            raise ValueError(f"scenes[{index}].id must be a non-empty string")
        if scene_id in seen_ids:
            raise ValueError(f"duplicate scene id: {scene_id}")
        seen_ids.add(scene_id)

        source_value = raw.get("source")
        if not isinstance(source_value, str) or not source_value.strip():
            raise ValueError(f"scenes[{index}].source must be a non-empty string")
        source = (plan_path.parent / source_value).resolve()
        if not source.is_file():
            raise ValueError(f"source recording does not exist: {source_value}")

        probe = probe_media(ffprobe, source)
        streams = probe.get("streams", [])
        if not any(stream.get("codec_type") == "video" for stream in streams):
            raise ValueError(f"source has no video stream: {source_value}")
        try:
            source_duration = float(probe["format"]["duration"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"source duration is unavailable: {source_value}") from exc

        start = finite_number(raw.get("start", 0), f"scenes[{index}].start")
        if start >= source_duration:
            raise ValueError(f"scene {scene_id} starts after source duration {source_duration:.3f}s")

        narration = None
        narration_duration = None
        narration_value = raw.get("narration")
        if narration_value is not None:
            if not isinstance(narration_value, str) or not narration_value.strip():
                raise ValueError(f"scenes[{index}].narration must be a non-empty string")
            narration = (plan_path.parent / narration_value).resolve()
            if not narration.is_file():
                raise ValueError(f"scene narration does not exist: {narration_value}")
            narration_probe = probe_media(ffprobe, narration)
            if not any(stream.get("codec_type") == "audio" for stream in narration_probe.get("streams", [])):
                raise ValueError(f"scene narration has no audio stream: {narration_value}")
            try:
                narration_duration = float(narration_probe["format"]["duration"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"scene narration duration is unavailable: {narration_value}") from exc

        default_duration = narration_duration if narration_duration is not None else source_duration - start
        duration = finite_number(raw.get("duration", default_duration), f"scenes[{index}].duration", 0.001)
        if narration_duration is not None and duration + 0.05 < narration_duration:
            raise ValueError(
                f"scene {scene_id} duration {duration:.3f}s truncates "
                f"narration duration {narration_duration:.3f}s"
            )
        available_source = source_duration - start
        requested_source_duration = finite_number(
            raw.get("source_duration", available_source),
            f"scenes[{index}].source_duration",
            0.001,
        )
        if requested_source_duration > available_source + 0.05:
            raise ValueError(f"scene {scene_id} source_duration exceeds available source")
        source_play_seconds = min(duration, requested_source_duration)
        video_extended_seconds = max(0.0, duration - source_play_seconds)
        if narration is None and video_extended_seconds > 0.05:
            raise ValueError(
                f"scene {scene_id} ends at {start + duration:.3f}s, "
                f"after source duration {source_duration:.3f}s"
            )

        captions = None
        caption_segments: list[dict[str, Any]] = []
        captions_value = raw.get("captions")
        if captions_value is not None:
            if not isinstance(captions_value, str) or not captions_value.strip():
                raise ValueError(f"scenes[{index}].captions must be a non-empty string")
            captions = (plan_path.parent / captions_value).resolve()
            if not captions.is_file():
                raise ValueError(f"scene captions do not exist: {captions_value}")
            caption_segments = read_captions(captions, scene_id, duration)

        background = None
        content_box = None
        if "background" in raw:
            background_value = raw.get("background")
            if not isinstance(background_value, str) or not background_value.strip():
                raise ValueError(f"scenes[{index}].background must be a non-empty string")
            background = (plan_path.parent / background_value).resolve()
            if not background.is_file():
                raise ValueError(f"scene background does not exist: {background_value}")
            if background.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                raise ValueError(f"scene background must be PNG, JPEG, or WebP: {background_value}")
            raw_box = raw.get("content_box")
            if not isinstance(raw_box, dict):
                raise ValueError(f"scenes[{index}].content_box is required with background")
            content_box = {
                "x": nonnegative_int(raw_box.get("x"), f"scenes[{index}].content_box.x"),
                "y": nonnegative_int(raw_box.get("y"), f"scenes[{index}].content_box.y"),
                "width": positive_int(raw_box.get("width"), f"scenes[{index}].content_box.width"),
                "height": positive_int(raw_box.get("height"), f"scenes[{index}].content_box.height"),
            }
            if content_box["width"] % 2 or content_box["height"] % 2:
                raise ValueError(f"scenes[{index}].content_box width and height must be even")
            if content_box["x"] + content_box["width"] > settings["width"] or content_box["y"] + content_box["height"] > settings["height"]:
                raise ValueError(f"scenes[{index}].content_box must fit inside the output frame")
        scenes.append(
            {
                "id": scene_id,
                "source": source,
                "source_ref": source_value,
                "start": start,
                "duration": duration,
                "source_duration": source_play_seconds,
                "has_audio": any(stream.get("codec_type") == "audio" for stream in streams),
                "narration": narration,
                "narration_ref": narration_value,
                "narration_duration": narration_duration,
                "video_extended_seconds": video_extended_seconds,
                "captions": captions,
                "captions_ref": captions_value,
                "caption_segments": caption_segments,
                "background": background,
                "background_ref": raw.get("background"),
                "content_box": content_box,
            }
        )
    return settings, scenes


def render_scene(ffmpeg: str, scene: dict[str, Any], settings: dict[str, int], destination: Path) -> None:
    duration = scene["duration"]
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{scene['start']:.6f}",
        "-i",
        str(scene["source"]),
    ]
    next_input = 1
    background_input = None
    if scene["background"]:
        background_input = next_input
        next_input += 1
        command += ["-loop", "1", "-framerate", str(settings["fps"]), "-i", str(scene["background"])]
    narration_input = None
    if scene["narration"]:
        narration_input = next_input
        next_input += 1
        command += ["-i", str(scene["narration"])]
    silent_input = None
    if narration_input is None and not scene["has_audio"]:
        silent_input = next_input
        command += [
            "-f",
            "lavfi",
            "-t",
            f"{duration:.6f}",
            "-i",
            f"anullsrc=r={settings['sample_rate']}:cl=stereo",
        ]
    command += ["-t", f"{duration:.6f}"]
    video_extension = scene["video_extended_seconds"]
    source_trim = f"trim=duration={scene['source_duration']:.6f},setpts=PTS-STARTPTS,"
    hold_filter = f",tpad=stop_mode=clone:stop_duration={video_extension:.6f}" if video_extension > 0.0 else ""
    caption_filter = ""
    if scene["caption_segments"]:
        ass_path = destination.with_suffix(".ass")
        write_ass(ass_path, scene["caption_segments"], settings)
        caption_filter = f",ass=filename='{ass_filter_path(ass_path)}'"
    if scene["background"]:
        box = scene["content_box"]
        command += [
            "-filter_complex",
            (
                f"[0:v]{source_trim}scale={box['width']}:{box['height']}:force_original_aspect_ratio=decrease,"
                f"pad={box['width']}:{box['height']}:(ow-iw)/2:(oh-ih)/2:color=black{hold_filter}[content];"
                f"[{background_input}:v]scale={settings['width']}:{settings['height']}[background];"
                f"[background][content]overlay={box['x']}:{box['y']}:shortest=1,"
                f"fps={settings['fps']},format=yuv420p{caption_filter}[video]"
            ),
            "-map",
            "[video]",
        ]
    else:
        command += [
            "-map",
            "0:v:0",
            "-vf",
            (
            f"{source_trim}scale={settings['width']}:{settings['height']}:force_original_aspect_ratio=decrease,"
            f"pad={settings['width']}:{settings['height']}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"fps={settings['fps']},format=yuv420p{hold_filter}{caption_filter}"
            ),
        ]
    audio_input = narration_input if narration_input is not None else (0 if scene["has_audio"] else silent_input)
    command += [
        "-map",
        f"{audio_input}:a:0",
        "-af",
        f"aresample={settings['sample_rate']},apad=whole_dur={duration:.6f}",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        str(settings["sample_rate"]),
        "-ac",
        "2",
        str(destination),
    ]
    run(command)


def concat_file_line(path: Path) -> str:
    escaped = path.resolve().as_posix().replace("'", "'\\''")
    return f"file '{escaped}'"


def build(plan_path: Path, output_dir: Path) -> tuple[Path, Path]:
    ffmpeg = require_tool("ffmpeg")
    ffprobe = require_tool("ffprobe")
    plan = read_json(plan_path)
    settings, scenes = validate_plan(plan_path, plan, ffprobe)
    output_dir.mkdir(parents=True, exist_ok=True)
    slug_value = plan.get("slug", plan_path.stem)
    if not isinstance(slug_value, str):
        raise ValueError("slug must be a string")
    output = next_output(output_dir, safe_slug(slug_value))

    with tempfile.TemporaryDirectory(prefix="course-video-", dir=output_dir) as temp_value:
        temp_dir = Path(temp_value)
        normalized: list[Path] = []
        for index, scene in enumerate(scenes):
            clip = temp_dir / f"scene_{index:03d}.mp4"
            render_scene(ffmpeg, scene, settings, clip)
            normalized.append(clip)
        concat_path = temp_dir / "concat.txt"
        concat_path.write_text("\n".join(concat_file_line(path) for path in normalized) + "\n", encoding="utf-8")
        staging = temp_dir / output.name
        run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(staging),
            ]
        )
        shutil.move(str(staging), output)

    final_probe = probe_media(ffprobe, output)
    manifest = output.with_suffix(".run.json")
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "plan": plan_path.name,
                "output": output.name,
                "video": settings,
                "scenes": [
                    {
                        "id": scene["id"],
                        "source": scene["source_ref"],
                        "start": scene["start"],
                        "duration": scene["duration"],
                        "source_duration": scene["source_duration"],
                        "source_has_audio": scene["has_audio"],
                        "narration": scene["narration_ref"],
                        "narration_duration": scene["narration_duration"],
                        "video_extended_seconds": scene["video_extended_seconds"],
                        "captions": scene["captions_ref"],
                        "caption_count": len(scene["caption_segments"]),
                        "background": scene["background_ref"],
                        "content_box": scene["content_box"],
                    }
                    for scene in scenes
                ],
                "probe": final_probe,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a practical-course video from real source recordings.")
    parser.add_argument("plan", type=Path, help="JSON scene plan; source paths are relative to this file.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for versioned MP4 and run manifest.")
    args = parser.parse_args()
    try:
        output, manifest = build(args.plan.resolve(), args.output_dir.resolve())
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"video": str(output), "manifest": str(manifest)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
