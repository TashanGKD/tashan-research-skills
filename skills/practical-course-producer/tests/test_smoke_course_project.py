from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SMOKE = SKILL_ROOT / "scripts" / "smoke_course_project.py"


def snapshot(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class CourseProjectSmokeTests(unittest.TestCase):
    def test_public_project_smoke_is_portable_and_leaves_checkout_unchanged(self) -> None:
        before = snapshot(SKILL_ROOT)
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        with tempfile.TemporaryDirectory(prefix="course-smoke-cwd-") as unrelated_cwd:
            result = subprocess.run(
                [sys.executable, str(SMOKE)],
                cwd=unrelated_cwd,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
        after = snapshot(SKILL_ROOT)

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertTrue(payload["checkout_unchanged"])
        self.assertEqual(payload["representative_frames"], 3)
        self.assertEqual(payload["final_gate"], "release")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
