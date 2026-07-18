from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class SkillBoundaryTests(unittest.TestCase):
    def test_behavior_evals_cover_success_blocking_and_routing(self) -> None:
        payload = json.loads((SKILL_ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["skill_name"], "practical-course-producer")
        ids = {case["id"] for case in payload["evals"]}
        self.assertEqual(ids, {"cli-workflow", "browser-workflow", "missing-real-evidence"})
        self.assertTrue(all(case["expectations"] for case in payload["evals"]))

    def test_trigger_queries_separate_workflows_from_concept_explainers(self) -> None:
        queries = json.loads((SKILL_ROOT / "evals" / "trigger_queries.json").read_text(encoding="utf-8"))
        positives = [item for item in queries if item["should_trigger"]]
        negatives = [item for item in queries if not item["should_trigger"]]
        self.assertGreaterEqual(len(positives), 4)
        self.assertGreaterEqual(len(negatives), 4)
        negative_text = " ".join(item["query"].lower() for item in negatives)
        self.assertIn("manim", negative_text)
        self.assertIn("concept", negative_text)


if __name__ == "__main__":
    unittest.main()
