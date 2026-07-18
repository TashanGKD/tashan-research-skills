from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
BUILDER = SKILL_ROOT / "scripts" / "build_course_video.py"
FIXTURE = Path(__file__).parent / "fixtures" / "scene-plan.json"


class CourseVideoBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ffmpeg = shutil.which("ffmpeg")
        cls.ffprobe = shutil.which("ffprobe")
        if not cls.ffmpeg or not cls.ffprobe:
            raise unittest.SkipTest("ffmpeg and ffprobe are required")

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="course-video-test-")
        self.root = Path(self.temp.name)
        self.output_dir = self.root / "outputs"
        self.plan = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self._make_sources()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )

    def _checked(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        result = self._run(command)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return result

    def _make_sources(self) -> None:
        self._checked(
            [
                self.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=400x240:rate=24:duration=1.2",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=660:sample_rate=44100:duration=1.2",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(self.root / "with-audio.mp4"),
            ]
        )
        self._checked(
            [
                self.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=240x240:rate=25:duration=1.0",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(self.root / "without-audio.mp4"),
            ]
        )
        self._checked(
            [
                self.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0xeff4f2:size=320x180",
                "-frames:v",
                "1",
                str(self.root / "frame.png"),
            ]
        )
        self._checked(
            [
                self.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=48000:duration=1.6",
                str(self.root / "narration.wav"),
            ]
        )

    def _write_plan(self, name: str = "plan.json") -> Path:
        path = self.root / name
        path.write_text(json.dumps(self.plan, indent=2) + "\n", encoding="utf-8")
        return path

    def _build(self, plan_path: Path) -> subprocess.CompletedProcess[str]:
        return self._run(
            [
                sys.executable,
                str(BUILDER),
                str(plan_path),
                "--output-dir",
                str(self.output_dir),
            ]
        )

    def _probe(self, path: Path) -> dict:
        result = self._checked(
            [
                self.ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,width,height,r_frame_rate,sample_rate,channels",
                "-of",
                "json",
                str(path),
            ]
        )
        return json.loads(result.stdout)

    def test_valid_build_is_versioned_and_normalized(self) -> None:
        plan_path = self._write_plan()
        first = self._build(plan_path)
        second = self._build(plan_path)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)

        first_result = json.loads(first.stdout)
        second_result = json.loads(second.stdout)
        self.assertTrue(first_result["video"].endswith("course-smoke_v001.mp4"))
        self.assertTrue(second_result["video"].endswith("course-smoke_v002.mp4"))

        probe = self._probe(Path(second_result["video"]))
        video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
        audio = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
        self.assertEqual((video["width"], video["height"]), (320, 180))
        self.assertEqual(video["r_frame_rate"], "30/1")
        self.assertEqual(audio["sample_rate"], "48000")
        self.assertEqual(audio["channels"], 2)
        self.assertAlmostEqual(float(probe["format"]["duration"]), 1.1, delta=0.12)

    def test_video_only_source_receives_audio_track(self) -> None:
        self.plan["slug"] = "silent-source"
        self.plan["scenes"] = [self.plan["scenes"][1]]
        result = self._build(self._write_plan("silent-plan.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        probe = self._probe(Path(json.loads(result.stdout)["video"]))
        audio_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "audio"]
        self.assertEqual(len(audio_streams), 1)
        self.assertEqual(audio_streams[0]["sample_rate"], "48000")

    def test_scene_can_use_a_framed_content_area(self) -> None:
        self.plan["slug"] = "framed-scene"
        self.plan["scenes"] = [self.plan["scenes"][0]]
        self.plan["scenes"][0]["background"] = "frame.png"
        self.plan["scenes"][0]["content_box"] = {"x": 40, "y": 30, "width": 220, "height": 120}
        result = self._build(self._write_plan("framed-plan.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(Path(json.loads(result.stdout)["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["scenes"][0]["background"], "frame.png")
        self.assertEqual(manifest["scenes"][0]["content_box"]["width"], 220)

    def test_narration_sets_duration_and_extends_the_last_video_frame(self) -> None:
        self.plan["slug"] = "narrated-scene"
        scene = self.plan["scenes"][1]
        scene.pop("duration", None)
        scene["narration"] = "narration.wav"
        self.plan["scenes"] = [scene]

        result = self._build(self._write_plan("narrated-plan.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        probe = self._probe(Path(payload["video"]))
        manifest = json.loads(Path(payload["manifest"]).read_text(encoding="utf-8"))

        self.assertAlmostEqual(float(probe["format"]["duration"]), 1.6, delta=0.12)
        self.assertEqual(manifest["scenes"][0]["narration"], "narration.wav")
        self.assertGreater(manifest["scenes"][0]["video_extended_seconds"], 0.5)

    def test_scene_duration_cannot_truncate_narration(self) -> None:
        self.plan["slug"] = "truncated-narration"
        scene = self.plan["scenes"][1]
        scene["duration"] = 1.0
        scene["narration"] = "narration.wav"
        self.plan["scenes"] = [scene]

        result = self._build(self._write_plan("truncated-narration-plan.json"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("truncates narration duration", result.stderr)
        self.assertFalse(list(self.output_dir.glob("truncated-narration_v*.mp4")))

    def test_scene_burns_sentence_timeline_as_captions(self) -> None:
        timeline = self.root / "narration.timeline.json"
        timeline.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "segments": [
                        {"text": "先检查原始文件。", "start": 0.25, "end": 0.85},
                        {"text": "然后重新验证。", "start": 0.9, "end": 1.5},
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.plan["slug"] = "captioned-scene"
        scene = self.plan["scenes"][1]
        scene.pop("duration", None)
        scene["narration"] = "narration.wav"
        scene["captions"] = "narration.timeline.json"
        self.plan["scenes"] = [scene]

        result = self._build(self._write_plan("captioned-plan.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(Path(json.loads(result.stdout)["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["scenes"][0]["captions"], "narration.timeline.json")
        self.assertEqual(manifest["scenes"][0]["caption_count"], 2)

    def test_scene_can_hold_after_a_bounded_source_segment(self) -> None:
        self.plan["slug"] = "bounded-source"
        scene = self.plan["scenes"][1]
        scene.pop("duration", None)
        scene["source_duration"] = 0.4
        scene["narration"] = "narration.wav"
        self.plan["scenes"] = [scene]

        result = self._build(self._write_plan("bounded-source-plan.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(Path(json.loads(result.stdout)["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["scenes"][0]["source_duration"], 0.4)
        self.assertAlmostEqual(manifest["scenes"][0]["video_extended_seconds"], 1.2, delta=0.05)

    def test_invalid_trim_is_rejected_before_render(self) -> None:
        self.plan["slug"] = "invalid-trim"
        self.plan["scenes"][0]["duration"] = 9.0
        result = self._build(self._write_plan("invalid-plan.json"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("after source duration", result.stderr)
        self.assertFalse(list(self.output_dir.glob("invalid-trim_v*.mp4")))


if __name__ == "__main__":
    unittest.main()
