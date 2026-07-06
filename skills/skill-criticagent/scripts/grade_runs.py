#!/usr/bin/env python3
"""Grade host-agent eval runs against a skill's evals.json.

The host agent runs each case twice (with/without the skill), collects final
answers plus any produced files (and a transcript.txt), then hands this script
a runs manifest. Grading is fully deterministic via the repo kernel.

Manifest format:
{
  "runs": [
    {
      "prompt": "<exact prompt string from evals.json>",
      "with_skill":    {"output": "...", "output_file": "path", "outputs_dir": "path"},
      "without_skill": {"output": "...", "output_file": "path", "outputs_dir": "path"}
    }
  ]
}
`output_file` (read as text) may replace inline `output`; `outputs_dir` is
optional and feeds file_assertions (including the transcript.txt convention).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _find_repo_root() -> Path:
    """In-repo layout first; standalone copies set MCP_CRITICAGENT_ROOT."""

    candidate = Path(__file__).resolve().parents[3]
    if (candidate / "src" / "core" / "skill_runner.py").is_file():
        return candidate
    import os

    env_root = os.environ.get("MCP_CRITICAGENT_ROOT")
    if env_root and (Path(env_root) / "src" / "core" / "skill_runner.py").is_file():
        return Path(env_root)
    raise SystemExit(
        "ERROR: evaluation kernel not found. Run from inside the MCP-CriticAgent "
        "repository, or set MCP_CRITICAGENT_ROOT to the repository path."
    )


sys.path.insert(0, str(_find_repo_root()))

from src.core.skill_file_asserts import read_outputs_dir  # noqa: E402
from src.core.skill_runner import ProviderResult, run_skill_evals  # noqa: E402


class ManifestProvider:
    """Serves pre-recorded host-agent outputs, matched by case prompt.

    Matching tries longer prompts first so that a case whose prompt is a
    prefix of another case's prompt can never steal the longer case's runs.
    """

    def __init__(self, runs):
        self.runs = sorted(
            runs, key=lambda run: len(run.get("prompt") or ""), reverse=True
        )

    def complete(self, prompt: str) -> ProviderResult:
        mode = "with_skill" if "<skill" in prompt else "without_skill"
        for run in self.runs:
            if run.get("prompt") and run["prompt"] in prompt:
                spec = run.get(mode) or {}
                output = spec.get("output", "")
                if not output and spec.get("output_file"):
                    output = Path(spec["output_file"]).read_text(encoding="utf-8")
                if not output and not spec.get("outputs_dir"):
                    print(
                        f"WARNING: manifest entry for {run['prompt'][:50]!r} has no "
                        f"{mode} output/output_file/outputs_dir — grading empty output",
                        file=sys.stderr,
                    )
                files = (
                    read_outputs_dir(spec["outputs_dir"])
                    if spec.get("outputs_dir")
                    else []
                )
                return ProviderResult(output=output, output_files=files)
        raise SystemExit(
            f"ERROR: no manifest entry matches this case prompt: {prompt[-120:]!r}. "
            "Each manifest run needs the EXACT prompt string from evals.json."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", help="skill directory containing evals/evals.json")
    parser.add_argument("manifest", help="runs manifest JSON (see module docstring)")
    parser.add_argument("--output", help="also write the full result JSON here")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    runs = manifest.get("runs")
    if not isinstance(runs, list) or not runs:
        raise SystemExit("ERROR: manifest must contain a non-empty 'runs' array")

    try:
        result = run_skill_evals(
            args.skill_dir, target_provider=ManifestProvider(runs), baseline=True
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            f"ERROR: {exc}. The skill needs evals/evals.json — write eval cases "
            "first (see the skill-criticagent SKILL.md quick-evaluation step 2)."
        )
    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload)

    summary = result.summary
    uplift = summary.get("skill_uplift", {})
    if uplift.get("pass_rate_delta", 1) <= 0:
        print(
            "\nVERDICT HINT: pass_rate_delta <= 0 — the skill shows no measurable "
            "uplift on this eval set.",
            file=sys.stderr,
        )
    audit = summary.get("assertion_audit", {})
    for entry in audit.get("non_discriminating", []):
        print(
            f"AUDIT: non-discriminating assertion (passes both modes): "
            f"{entry['case_id']} :: {entry['assertion']}",
            file=sys.stderr,
        )
    for entry in audit.get("always_failing", []):
        print(
            f"AUDIT: always-failing assertion (fails both modes): "
            f"{entry['case_id']} :: {entry['assertion']}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
