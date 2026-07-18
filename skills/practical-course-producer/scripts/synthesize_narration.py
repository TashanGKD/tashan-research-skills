#!/usr/bin/env python
"""Generate narration audio plus provider-backed sentence timing metadata."""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_PROVIDER = "volcengine"
DEFAULT_FALLBACK_PROVIDER = "edge-tts"
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_RATE = "+0%"
DEFAULT_LEAD_IN_MS = 250
DEFAULT_TAIL_PAD_MS = 350
DEFAULT_VOLCENGINE_ENDPOINT = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
DEFAULT_VOLCENGINE_RESOURCE_ID = "seed-tts-2.0"
DEFAULT_VOLCENGINE_SPEAKER = "zh_female_vv_uranus_bigtts"
VOLCENGINE_API_KEY_CONSOLE_URL = "https://console.volcengine.com/speech/new/setting/apikeys?projectName=default"
VOLCENGINE_APP_KEY = "aGjiRDfUWi"
VOLCENGINE_TIMEOUT_SECONDS = 300


def spoken_text(markdown: str) -> str:
    lines: list[str] = []
    in_fence = False
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line or re.match(r"^#{1,6}\s+", line):
            continue
        line = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", line)
        line = re.sub(r"[`*_~]", "", line)
        line = re.sub(r"^[-+>]\s+", "", line)
        lines.append(line)
    text = "\n".join(lines).strip()
    if not text:
        raise ValueError("narration contains no spoken text")
    return text


def timeline_segments(metadata: list[dict[str, Any]], lead_in_ms: int) -> list[dict[str, Any]]:
    lead = lead_in_ms / 1000
    segments: list[dict[str, Any]] = []
    for item in metadata:
        if item.get("type") != "SentenceBoundary":
            continue
        start = float(item["offset"]) / 10_000_000 + lead
        end = start + float(item["duration"]) / 10_000_000
        segments.append({"text": str(item.get("text", "")), "start": round(start, 3), "end": round(end, 3)})
    for index in range(len(segments) - 1):
        segments[index]["end"] = min(segments[index]["end"], segments[index + 1]["start"])
    return segments


def parse_json_stream(body: bytes) -> list[dict[str, Any]]:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("Volcengine TTS returned invalid UTF-8") from exc
    decoder = json.JSONDecoder()
    index = 0
    events: list[dict[str, Any]] = []
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            break
        try:
            value, index = decoder.raw_decode(text, index)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Volcengine TTS returned an invalid JSON stream") from exc
        if not isinstance(value, dict):
            raise RuntimeError("Volcengine TTS returned a non-object stream event")
        events.append(value)
    return events


def volcengine_segments(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for event in events:
        sentence = event.get("sentence")
        if not isinstance(sentence, dict):
            continue
        words = sentence.get("words")
        if not isinstance(words, list) or not words:
            continue
        try:
            start = float(words[0]["startTime"])
            end = float(words[-1]["endTime"])
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        if end <= start:
            continue
        segments.append({"text": str(sentence.get("text", "")), "start": round(start, 3), "end": round(end, 3)})
    return segments


def shift_segments(segments: list[dict[str, Any]], lead_in_ms: int) -> list[dict[str, Any]]:
    lead = lead_in_ms / 1000
    return [
        {"text": item["text"], "start": round(float(item["start"]) + lead, 3), "end": round(float(item["end"]) + lead, 3)}
        for item in segments
    ]


def redact(message: str, secret: str | None) -> str:
    return message.replace(secret, "<redacted>") if secret else message


def volcengine_api_key_help(message: str) -> str:
    return (
        f"{message}. Get or replace the API key at {VOLCENGINE_API_KEY_CONSOLE_URL} "
        "and set VOLCENGINE_TTS_API_KEY in the environment"
    )


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
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"required executable is not on PATH: {name}")
    return path


async def edge_save(text: str, audio: Path, metadata: Path, voice: str, rate: str, volume: str, pitch: str) -> None:
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("edge-tts is required: python -m pip install edge-tts") from exc
    last_error: Exception | None = None
    for attempt in range(3):
        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
            boundary="SentenceBoundary",
        )
        try:
            await communicate.save(str(audio), str(metadata))
            return
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(attempt + 1)
    raise RuntimeError(f"no audio after 3 attempts: {last_error}")


def volcengine_save(
    text: str,
    audio: Path,
    api_key: str | None,
    speaker: str | None,
    resource_id: str,
    endpoint: str,
) -> dict[str, Any]:
    if not api_key:
        raise RuntimeError(volcengine_api_key_help("VOLCENGINE_TTS_API_KEY is not set"))
    if len(text) > 3000:
        raise RuntimeError("Volcengine TTS text exceeds the 3000-character single-request limit")

    payload = {
        "user": {"uid": "practical-course-producer"},
        "req_params": {
            "text": text,
            "speaker": speaker or DEFAULT_VOLCENGINE_SPEAKER,
            "audio_params": {
                "format": "mp3",
                "sample_rate": 48000,
                "speech_rate": 0,
                "loudness_rate": 0,
                "enable_subtitle": True,
            },
            "additions": json.dumps(
                {"disable_markdown_filter": True, "enable_timestamp": True},
                separators=(",", ":"),
            ),
        },
    }
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": api_key,
            "X-Api-Resource-Id": resource_id,
            "X-Api-App-Key": VOLCENGINE_APP_KEY,
            "X-Api-Request-Id": str(uuid.uuid4()),
        },
        method="POST",
    )

    for attempt in range(3):
        try:
            with urlopen(request, timeout=VOLCENGINE_TIMEOUT_SECONDS) as response:
                body = response.read()
                log_id = response.headers.get("X-Tt-Logid")
            break
        except HTTPError as exc:
            detail = redact(exc.read().decode("utf-8", errors="replace"), api_key)[:500]
            if exc.code == 401:
                raise RuntimeError(volcengine_api_key_help("Volcengine API key was rejected (HTTP 401)")) from exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise RuntimeError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
        except URLError as exc:
            if attempt == 2:
                raise RuntimeError(f"network error: {redact(str(exc.reason), api_key)}") from exc
        time.sleep(attempt + 1)
    else:  # pragma: no cover - loop always breaks or raises
        raise RuntimeError("Volcengine TTS request failed")

    events = parse_json_stream(body)
    audio_parts: list[bytes] = []
    terminal_seen = False
    for event in events:
        code = event.get("code")
        if code == 20000000:
            terminal_seen = True
            continue
        if code not in (None, 0):
            message = redact(str(event.get("message", "unknown provider error")), api_key)
            if code == 45000010 or "invalid x-api-key" in message.lower() or "invalid api key" in message.lower():
                raise RuntimeError(volcengine_api_key_help(f"Volcengine API key was rejected (provider code {code})"))
            raise RuntimeError(f"provider code {code}: {message}")
        if event.get("data"):
            try:
                audio_parts.append(base64.b64decode(event["data"], validate=True))
            except (ValueError, binascii.Error) as exc:
                raise RuntimeError("Volcengine TTS returned invalid base64 audio") from exc
    if not terminal_seen:
        raise RuntimeError("Volcengine TTS stream ended without a success event")
    if not audio_parts:
        raise RuntimeError("Volcengine TTS returned no audio chunks")
    audio.write_bytes(b"".join(audio_parts))

    segments = volcengine_segments(events)
    if not segments:
        raise RuntimeError("Volcengine TTS returned no timestamped sentences")
    return {"segments": segments, "log_id": log_id}


def generate_raw_audio(
    *,
    text: str,
    raw_audio: Path,
    raw_metadata: Path,
    provider: str,
    fallback_provider: str,
    api_key: str | None,
    speaker: str | None,
    resource_id: str,
    endpoint: str,
    voice: str,
    rate: str,
    volume: str,
    pitch: str,
    lead_in_ms: int,
) -> dict[str, Any]:
    if provider == "edge-tts":
        asyncio.run(edge_save(text, raw_audio, raw_metadata, voice, rate, volume, pitch))
        metadata = [json.loads(line) for line in raw_metadata.read_text(encoding="utf-8").splitlines() if line.strip()]
        segments = timeline_segments(metadata, lead_in_ms)
        if not segments:
            raise RuntimeError("Edge TTS returned no sentence boundaries")
        return {
            "provider": "edge-tts",
            "voice": voice,
            "timing_source": "provider_sentence_boundaries",
            "segments": segments,
            "fallback_used": False,
        }
    if provider != "volcengine":
        raise ValueError(f"unsupported TTS provider: {provider}")

    try:
        result = volcengine_save(text, raw_audio, api_key, speaker, resource_id, endpoint)
        return {
            "provider": "volcengine",
            "voice": speaker,
            "resource_id": resource_id,
            "timing_source": "provider_word_timestamps",
            "segments": shift_segments(result["segments"], lead_in_ms),
            "fallback_used": False,
            "provider_log_id": result.get("log_id"),
        }
    except Exception as exc:
        reason = redact(str(exc), api_key)
        if fallback_provider != "edge-tts":
            raise RuntimeError(f"Volcengine TTS failed: {reason}") from exc
        try:
            asyncio.run(edge_save(text, raw_audio, raw_metadata, voice, rate, volume, pitch))
            metadata = [json.loads(line) for line in raw_metadata.read_text(encoding="utf-8").splitlines() if line.strip()]
            segments = timeline_segments(metadata, lead_in_ms)
            if not segments:
                raise RuntimeError("Edge TTS returned no sentence boundaries")
        except Exception as fallback_exc:
            fallback_detail = redact(str(fallback_exc), api_key)
            raise RuntimeError(f"Volcengine TTS failed: {reason}; Edge TTS fallback failed: {fallback_detail}") from fallback_exc
        return {
            "provider": "edge-tts",
            "voice": voice,
            "timing_source": "provider_sentence_boundaries",
            "segments": segments,
            "fallback_used": True,
            "fallback_from": "volcengine",
            "fallback_reason": reason,
        }


def synthesize(
    source: Path,
    output: Path,
    timeline: Path,
    voice: str,
    rate: str,
    volume: str,
    pitch: str,
    lead_in_ms: int,
    tail_pad_ms: int,
    provider: str = DEFAULT_PROVIDER,
    fallback_provider: str = DEFAULT_FALLBACK_PROVIDER,
    api_key: str | None = None,
    speaker: str | None = None,
    resource_id: str = DEFAULT_VOLCENGINE_RESOURCE_ID,
    endpoint: str = DEFAULT_VOLCENGINE_ENDPOINT,
) -> dict[str, Any]:
    if lead_in_ms < 0 or tail_pad_ms < 0:
        raise ValueError("lead-in and tail padding must be non-negative")
    if output.suffix.lower() not in {".mp3", ".wav"}:
        raise ValueError("output must use .mp3 or .wav")
    text = spoken_text(source.read_text(encoding="utf-8"))
    ffmpeg = require_tool("ffmpeg")
    ffprobe = require_tool("ffprobe")
    output.parent.mkdir(parents=True, exist_ok=True)
    timeline.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="course-tts-", dir=output.parent) as temp_value:
        temp = Path(temp_value)
        raw_audio = temp / "narration.mp3"
        raw_metadata = temp / "boundaries.jsonl"
        provider_result = generate_raw_audio(
            text=text,
            raw_audio=raw_audio,
            raw_metadata=raw_metadata,
            provider=provider,
            fallback_provider=fallback_provider,
            api_key=api_key,
            speaker=speaker,
            resource_id=resource_id,
            endpoint=endpoint,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
            lead_in_ms=lead_in_ms,
        )

        audio_filter = f"adelay={lead_in_ms}:all=1,apad=pad_dur={tail_pad_ms / 1000:.3f}"
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(raw_audio),
            "-af",
            audio_filter,
            "-ar",
            "48000",
            "-ac",
            "2",
        ]
        if output.suffix.lower() == ".mp3":
            command += ["-c:a", "libmp3lame", "-b:a", "192k"]
        else:
            command += ["-c:a", "pcm_s16le"]
        run(command + [str(output)])

    duration = float(
        run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(output),
            ]
        ).stdout.strip()
    )
    timeline_payload = {
        "schema_version": 1,
        "requested_provider": provider,
        "provider": provider_result["provider"],
        "fallback_provider": fallback_provider,
        "fallback_used": provider_result["fallback_used"],
        "voice": provider_result["voice"],
        "resource_id": provider_result.get("resource_id"),
        "timing_source": provider_result["timing_source"],
        "rate": rate if provider_result["provider"] == "edge-tts" else "normal",
        "volume": volume if provider_result["provider"] == "edge-tts" else "normal",
        "pitch": pitch if provider_result["provider"] == "edge-tts" else "normal",
        "lead_in_ms": lead_in_ms,
        "tail_pad_ms": tail_pad_ms,
        "source": source.name,
        "audio": output.name,
        "audio_duration_seconds": round(duration, 3),
        "segments": provider_result["segments"],
    }
    for key in ("fallback_from", "fallback_reason", "provider_log_id"):
        if provider_result.get(key) is not None:
            timeline_payload[key] = provider_result[key]
    timeline.write_text(json.dumps(timeline_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "audio": str(output),
        "timeline": str(timeline),
        "duration": round(duration, 3),
        "segments": len(provider_result["segments"]),
        "provider": provider_result["provider"],
        "fallback_used": provider_result["fallback_used"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate narration and provider-backed sentence timing data.")
    parser.add_argument("source", type=Path, help="Markdown narration source")
    parser.add_argument("--output", type=Path, required=True, help="Output MP3 or WAV")
    parser.add_argument("--timeline", type=Path, help="Output timeline JSON; defaults beside audio")
    parser.add_argument("--provider", choices=("volcengine", "edge-tts"), default=DEFAULT_PROVIDER)
    parser.add_argument("--fallback-provider", choices=("edge-tts", "none"), default=DEFAULT_FALLBACK_PROVIDER)
    parser.add_argument("--speaker", default=os.environ.get("VOLCENGINE_TTS_SPEAKER", DEFAULT_VOLCENGINE_SPEAKER))
    parser.add_argument(
        "--volcengine-resource-id",
        default=os.environ.get("VOLCENGINE_TTS_RESOURCE_ID", DEFAULT_VOLCENGINE_RESOURCE_ID),
    )
    parser.add_argument("--volcengine-endpoint", default=os.environ.get("VOLCENGINE_TTS_ENDPOINT", DEFAULT_VOLCENGINE_ENDPOINT))
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Edge TTS voice used for fallback or direct Edge synthesis")
    parser.add_argument("--rate", default=DEFAULT_RATE, help="Edge TTS rate used for fallback or direct Edge synthesis")
    parser.add_argument("--volume", default="+0%", help="Edge TTS volume")
    parser.add_argument("--pitch", default="+0Hz", help="Edge TTS pitch")
    parser.add_argument("--lead-in-ms", type=int, default=DEFAULT_LEAD_IN_MS)
    parser.add_argument("--tail-pad-ms", type=int, default=DEFAULT_TAIL_PAD_MS)
    args = parser.parse_args()
    output = args.output.resolve()
    timeline = args.timeline.resolve() if args.timeline else output.with_suffix(".timeline.json")
    try:
        payload = synthesize(
            args.source.resolve(),
            output,
            timeline,
            args.voice,
            args.rate,
            args.volume,
            args.pitch,
            args.lead_in_ms,
            args.tail_pad_ms,
            provider=args.provider,
            fallback_provider=args.fallback_provider,
            api_key=os.environ.get("VOLCENGINE_TTS_API_KEY"),
            speaker=args.speaker,
            resource_id=args.volcengine_resource_id,
            endpoint=args.volcengine_endpoint,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
