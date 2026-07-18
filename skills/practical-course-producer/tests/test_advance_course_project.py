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
RUNNER = SKILL_ROOT / "scripts" / "advance_course_project.py"
PUBLIC_FIXTURE = SKILL_ROOT / "tests" / "fixtures" / "course-project"


class AdvanceCourseProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ffmpeg = shutil.which("ffmpeg")
        cls.ffprobe = shutil.which("ffprobe")
        if not cls.ffmpeg or not cls.ffprobe:
            raise unittest.SkipTest("ffmpeg and ffprobe are required")

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="advance-course-project-")
        self.root = Path(self.temp.name)
        self.project_path = self.root / "course-project.json"
        self.project = {
            "schema_version": 1,
            "slug": "orchestrated-course",
            "topic": "A real tool workflow",
            "audience": "research tool users",
            "language": "zh-CN",
            "target_duration_seconds": 0.6,
            "aspect_ratio": "16:9",
            "artifacts": {
                "lesson_plan": "lesson-plan.md",
                "interaction_plan": "interaction-plan.md",
                "recording_checklist": "recording-checklist.md",
                "narration": "narration.md",
                "scene_plan": "course-plan.json",
                "final_video": "outputs/pending.mp4",
                "run_manifest": "outputs/pending.run.json",
                "audit": "audit.md",
            },
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_project(self) -> None:
        self.project_path.write_text(json.dumps(self.project, indent=2) + "\n", encoding="utf-8")

    def _write(self, relative: str, content: str = "evidence\n") -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _run(self, target: str = "render") -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(RUNNER), str(self.project_path), "--to", target],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )

    def _complete_record_gate(self) -> None:
        for name in ("lesson-plan.md", "interaction-plan.md", "recording-checklist.md", "narration.md"):
            self._write(name)
        self._make_recording()
        self._write(
            "course-plan.json",
            json.dumps(
                {
                    "slug": "orchestrated-course",
                    "video": {"width": 320, "height": 180, "fps": 30, "sample_rate": 48000},
                    "scenes": [{"id": "demo", "source": "recordings/demo.mp4", "duration": 0.6}],
                },
                indent=2,
            )
            + "\n",
        )

    def _make_recording(self) -> None:
        recordings = self.root / "recordings"
        recordings.mkdir(exist_ok=True)
        made = subprocess.run(
            [
                self.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
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
                str(recordings / "demo.mp4"),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(made.returncode, 0, made.stderr)

    def test_render_stops_when_project_has_not_passed_record_gate(self) -> None:
        self._write_project()
        result = self._run()
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["blocked_at"], "record")
        self.assertFalse((self.root / "outputs").exists())

    def test_render_builds_media_and_updates_the_project_contract(self) -> None:
        self._complete_record_gate()
        self._write_project()
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        updated = json.loads(self.project_path.read_text(encoding="utf-8"))

        video = self.root / updated["artifacts"]["final_video"]
        manifest = self.root / updated["artifacts"]["run_manifest"]
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["gate"], "render")
        self.assertTrue(video.is_file())
        self.assertTrue(manifest.is_file())
        self.assertNotEqual(video.name, "pending.mp4")

    def test_release_stops_when_render_gate_has_not_passed(self) -> None:
        self._complete_record_gate()
        self._write_project()
        result = self._run("release")
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["blocked_at"], "render")
        self.assertFalse((self.root / "audit.md").exists())

    def test_release_writes_deterministic_media_evidence(self) -> None:
        self._complete_record_gate()
        self._write_project()
        rendered = self._run("render")
        self.assertEqual(rendered.returncode, 0, rendered.stderr or rendered.stdout)

        released = self._run("release")
        self.assertEqual(released.returncode, 0, released.stderr or released.stdout)
        payload = json.loads(released.stdout)
        report = (self.root / "audit.md").read_text(encoding="utf-8")
        frames = sorted((self.root / "audit-frames").glob("frame-*.png"))

        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["gate"], "release")
        self.assertIn("SHA-256", report)
        self.assertIn("Silence intervals", report)
        self.assertIn("Automated media integrity: PASS", report)
        self.assertEqual(len(frames), 3)

    def test_release_rejects_video_far_from_target_duration(self) -> None:
        self.project["target_duration_seconds"] = 60
        self._complete_record_gate()
        self._write_project()
        rendered = self._run("render")
        self.assertEqual(rendered.returncode, 0, rendered.stderr or rendered.stdout)

        released = self._run("release")
        self.assertEqual(released.returncode, 2)
        payload = json.loads(released.stdout)
        self.assertEqual(payload["blocked_at"], "release")
        self.assertIn("outside target duration range", payload["errors"][0])

    def test_public_fixture_advances_from_missing_recording_to_release(self) -> None:
        shutil.copytree(PUBLIC_FIXTURE, self.root, dirs_exist_ok=True)
        self.project_path = self.root / "course-project.json"

        blocked = self._run("record")
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("recordings/demo.mp4", blocked.stdout)

        self._make_recording()
        rendered = self._run("render")
        self.assertEqual(rendered.returncode, 0, rendered.stderr or rendered.stdout)
        released = self._run("release")
        self.assertEqual(released.returncode, 0, released.stderr or released.stdout)
        self.assertTrue((self.root / "audit.md").is_file())
        self.assertEqual(len(list((self.root / "audit-frames").glob("frame-*.png"))), 3)


if __name__ == "__main__":
    unittest.main()
