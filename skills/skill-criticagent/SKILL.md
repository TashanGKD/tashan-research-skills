---
name: skill-criticagent
description: Evaluate Agent Skills (SKILL.md directories) and answer "is this skill any good / safe to install" — spec compliance with security scanning, with/without behavior comparison, and description trigger testing, ending in a clear install / fix-first / reject verdict. Use this skill whenever the user asks to evaluate, audit, test, review, or score an Agent Skill or a skill collection, wants to know whether a skill actually helps or is safe, or wants to check if a skill's description triggers correctly, even if they just ask "is this skill any good".
---

# Skill-CriticAgent

You answer one question for the user: **should they install this skill?**
Everything else is your internal machinery — do the rigorous work, then report
in plain language. Never make the user operate the machinery.

The dependency-free deterministic kernel is bundled under
`vendor/mcp_criticagent/src/core/skill_*` and protected by a checked-in
SHA-256 manifest. No API keys are needed — you are the model.
`MCP_CRITICAGENT_ROOT` remains available only as an explicit development
override for testing another reviewed kernel checkout.

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

   Run each case once in each mode. Produce two answers (with_skill: follow
   the SKILL.md faithfully), execute real reads/writes when the task requires
   them, save produced files plus a short `transcript.txt` into an isolated
   per-case outputs dir, record the actual tool calls, and grade:

```bash
uv run python skills/skill-criticagent/scripts/grade_runs.py <skill_dir> <manifest.json>
```

   Manifest: `{"runs": [{"prompt": "<exact prompt from evals.json>",
   "with_skill": {"output": "..." or "output_file": "<abs path>",
   "outputs_dir": "<abs path>", "tool_calls": [<OpenAI-style calls>]},
   "without_skill": {...}}]}`. Use absolute paths (forward slashes are fine
   on Windows). A claimed file path in answer text is not evidence: require
   `file_assertions` against the real outputs directory. A claimed read/write
   is not evidence: require `tool_assertions` against the recorded calls.

   Before and after the run, hash every source input and `SKILL.md`; source
   hashes must remain unchanged. Archive the runs manifest, outputs, trace,
   grader JSON, and hashes. A behavior/trigger pass without this execution
   evidence is provisional and cannot support **建议安装**. A channel may be
   `not_applicable` only when the skill contract truly defines no such side
   effect, with an explicit rationale.

   In this repository, AgentScope + OpenAI-compatible provider runs use
   `skills/find-science-skills/scripts/run_agentscope_critic_provider.py`.
   It mounts the skill outside an isolated evaluation workspace, confines
   Write to that workspace, permits Read in the workspace and read-only mounted
   skill source, and permits Bash only for exact commands declared by the case.
   The complete run has a separate wall-clock limit. Provider, permission,
   timeout, or transport failures are execution failures and must not be scored
   as skill-quality failures.

3. **Does it trigger?** Use `<skill_dir>/evals/trigger_queries.json` if
   present; otherwise write ~8 queries yourself (half should trigger with
   varied phrasing, half near-misses that share keywords but need something
   else). For collection-scale quick evaluation, decide once per query whether
   you would activate the skill given only its name+description in your
   catalog, then score. Batch all queries in one isolated decision call when
   practical; preserve one decision per query in the grader input:

```bash
uv run python skills/skill-criticagent/scripts/grade_triggers.py <skill_dir> <decisions.json>
```

   When a supervising CriticAgent is re-adjudicating archived evidence, add
   `--report-only`: imperfect trigger accuracy still prints the same quality
   RED and `VERDICT HINT`, but it does not masquerade as a provider/tool
   execution failure. Keep the default failing exit code for standalone gates.

   Decisions: `[{"query": "...", "should_trigger": true, "decisions":
   ["<skill-name>"]}]`. Repeat each query three times only for deep evaluation,
   borderline results, or an explicit stability request.

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
to ~20, repeat each trigger decision three times, and share the full JSON
reports (`--output`). Multiple behavior iterations remain optional stability
evidence, not a prerequisite for a complete real run.

## Grading principles (for anything you grade yourself)

- Require concrete evidence for every PASS; quote the output or file.
- Do not give the benefit of the doubt; a label without substance is a FAIL.
- State the known limit: your trigger decisions are self-reported and may
  differ from real in-task activation.
