---
name: skill-criticagent
description: Evaluate Agent Skills (SKILL.md directories) and answer "is this skill any good / safe to install" — spec compliance with security scanning, with/without behavior comparison, and description trigger testing, ending in a clear install / fix-first / reject verdict. Use this skill whenever the user asks to evaluate, audit, test, review, or score an Agent Skill or a skill collection, wants to know whether a skill actually helps or is safe, or wants to check if a skill's description triggers correctly, even if they just ask "is this skill any good".
---

# Skill-CriticAgent

You answer one question for the user: **should they install this skill?**
Everything else is your internal machinery — do the rigorous work, then report
in plain language. Never make the user operate the machinery.

The deterministic kernel lives in this repository (`src/core/skill_*`). Run all
commands from the repository root; deps via `uv sync`. No API keys needed — you
are the model. (Standalone copies of this skill: set `MCP_CRITICAGENT_ROOT` to
the repository path.)

## Default: quick evaluation (zero questions asked)

Do all of this yourself without interviewing the user, then report.

1. **Compliance + security** (always first):

```bash
uv run python -m src.main eval-skill <skill_dir> --strict --json
```

   Errors mean it cannot install (bad frontmatter, name/directory mismatch,
   missing referenced files, script syntax errors, embedded secrets). If it
   fails, report the verdict as "先修复" (or "不建议安装" for secrets) with
   the reasons, and skip the rest — evaluating an uninstallable skill wastes
   everyone's time. Collections: `list-skills <root> --health --strict --json`.

2. **Does it help?** If `<skill_dir>/evals/evals.json` exists, use it — but
   check the assertions first: free-form sentence assertions (common in
   `expectations` fields) degrade to literal substring checks in this
   pipeline and would fail both rounds meaninglessly. When you see them, work
   on a temp copy of the skill and derive verifiable assertions from each
   sentence (specific strings/regex the correct behavior must contain), then
   state the derivation in your report. If no evals exist, write 3 realistic
   cases yourself from the skill's description (real-user phrasing, concrete
   details; verifiable assertions — text contains/regex, `file_assertions`
   for produced files).

   Baseline hygiene: the without-skill round must not be contaminated by your
   having read the skill — use a fresh subagent for it (instructed not to
   read the skill's files), or run it before reading the skill body.

   For each case, produce two answers (with_skill: follow the SKILL.md
   faithfully, save produced files plus a short `transcript.txt` into a
   per-case outputs dir), record them in a runs manifest, and grade:

```bash
uv run python skills/skill-criticagent/scripts/grade_runs.py <skill_dir> <manifest.json>
```

   Manifest: `{"runs": [{"prompt": "<exact prompt from evals.json>",
   "with_skill": {"output": "..." or "output_file": "<abs path>",
   "outputs_dir": "<abs path>"}, "without_skill": {...}}]}`. Use absolute
   paths (forward slashes are fine on Windows).

3. **Does it trigger?** Use `<skill_dir>/evals/trigger_queries.json` if
   present; otherwise write ~8 queries yourself (half should trigger with
   varied phrasing, half near-misses that share keywords but need something
   else). For each query, decide 3 times independently whether you would
   activate the skill given only its name+description in your catalog, then
   score:

```bash
uv run python skills/skill-criticagent/scripts/grade_triggers.py <skill_dir> <decisions.json>
```

   Decisions: `[{"query": "...", "should_trigger": true, "decisions":
   ["<skill-name>", "none", "<skill-name>"]}]`.

## The report (this is the deliverable)

Lead with the verdict, then one plain-language line per dimension, then only
the evidence that matters. Model:

> **结论：建议安装** ✅
>
> - **能不能装**：通过（规范合规，无安全发现）
> - **有没有用**：带上它 3 个任务全部做对，不带只对 1 个——提升明显
> - **会不会被用上**：8 条测试请求 7 条触发正确；"帮我处理这个表格"这类
>   不点名的请求可能不触发，description 可以补一句
>
> 关键证据：不带 skill 时两个任务的输出缺少 report.html / 引用了错误的 API。

Translation rules — never expose internal jargon:

- `pass_rate_delta` → counts: "带上它 X/N 做对，不带 Y/N"
- non-discriminating assertion (AUDIT hint on stderr) → judge before acting:
  it means the baseline ALSO passed, which happens either because the check
  is genuinely trivial (exclude it and say "有 N 条测试太简单，没算进结论")
  or because the baseline coincidentally knew that one fact while still
  failing the case overall (keep it — it is still a valid correctness check).
  Look at whether the baseline passed the whole case, not just the assertion.
- always-failing assertion → treat as a broken test, not a skill failure;
  mention only if it changed your verdict
- trigger_rate / threshold → "N 条里 M 条触发正确" plus which queries failed
- Skipped or unverifiable checks → say so plainly; never present partial
  coverage as a full evaluation

Verdict scale: **建议安装** (compliant, clear uplift, triggers correctly) /
**先修复** (fixable issues: validation errors, weak description, no uplift on
current instructions) / **不建议安装** (secrets or risky instructions, or
misleading behavior). One sentence of reasoning next to the verdict.

## On request only: deep evaluation

If the user asks for a rigorous benchmark, more confidence, or wants to
iterate on the skill: co-design eval cases with them, expand trigger queries
to ~20, run multiple iterations per case for stability, and share the full
JSON reports (`--output`). Do not default to any of this.

## Grading principles (for anything you grade yourself)

- Require concrete evidence for every PASS; quote the output or file.
- Do not give the benefit of the doubt; a label without substance is a FAIL.
- State the known limit: your trigger decisions are self-reported and may
  differ from real in-task activation.
