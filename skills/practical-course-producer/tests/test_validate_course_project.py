from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "validate_course_project.py"
TEMPLATE = SKILL_ROOT / "assets" / "course-project.json"


class CourseProjectValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="course-project-test-")
        self.root = Path(self.temp.name)
        self.project = {
            "schema_version": 1,
            "slug": "public-course",
            "topic": "Build a reusable research workflow",
            "audience": "researchers who use command-line tools",
            "language": "zh-CN",
            "target_duration_seconds": 300,
            "aspect_ratio": "16:9",
            "artifacts": {
                "lesson_plan": "lesson-plan.md",
                "interaction_plan": "interaction-plan.md",
                "recording_checklist": "recording-checklist.md",
                "narration": "narration.md",
                "scene_plan": "course-plan.json",
                "final_video": "outputs/course_v001.mp4",
                "run_manifest": "outputs/course_v001.run.json",
                "audit": "audit.md",
            },
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_project(self) -> Path:
        path = self.root / "course-project.json"
        path.write_text(json.dumps(self.project, indent=2) + "\n", encoding="utf-8")
        return path

    def _write(self, relative: str, content: str = "evidence\n") -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _run(self, gate: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(self._write_project()), "--gate", gate],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def _complete_plan(self) -> None:
        for name in ("lesson-plan.md", "interaction-plan.md", "recording-checklist.md", "narration.md"):
            self._write(name)

    def test_plan_gate_rejects_missing_planning_artifacts(self) -> None:
        result = self._run("plan")
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "fail")
        self.assertIn("artifacts.lesson_plan does not exist: lesson-plan.md", payload["errors"])

    def test_packaged_project_template_matches_the_validator_contract(self) -> None:
        template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(template["schema_version"], 1)
        self.assertEqual(set(template["artifacts"]), set(self.project["artifacts"]))

    def test_record_gate_requires_real_scene_sources(self) -> None:
        self._complete_plan()
        self._write(
            "course-plan.json",
            json.dumps({"scenes": [{"id": "demo", "source": "recordings/demo.mp4"}]}) + "\n",
        )
        result = self._run("record")
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertIn("scene demo source does not exist: recordings/demo.mp4", payload["errors"])

        self._write("recordings/demo.mp4", "recorded evidence")
        passed = self._run("record")
        self.assertEqual(passed.returncode, 0, passed.stdout)

    def test_release_gate_requires_render_manifest_and_audit(self) -> None:
        self._complete_plan()
        self._write("recordings/demo.mp4", "recorded evidence")
        self._write(
            "course-plan.json",
            json.dumps({"scenes": [{"id": "demo", "source": "recordings/demo.mp4"}]}) + "\n",
        )
        self._write("outputs/course_v001.mp4", "video")

        result = self._run("release")
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertIn("artifacts.run_manifest does not exist: outputs/course_v001.run.json", payload["errors"])
        self.assertIn("artifacts.audit does not exist: audit.md", payload["errors"])

        self._write("outputs/course_v001.run.json", "{}\n")
        self._write("audit.md", "ffprobe: pass\nframe audit: pass\n")
        passed = self._run("release")
        self.assertEqual(passed.returncode, 0, passed.stdout)


if __name__ == "__main__":
    unittest.main()
