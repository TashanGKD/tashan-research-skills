---
name: practical-course-producer
description: Generate and audit evidence-based practical course videos for executable software, research-tool, or AI-assisted workflows with observable real interaction and verification. Use when a user needs a publishable hands-on tutorial built from genuine terminal, browser, or tool operation, narration, demonstrations, corrections, and checks instead of simulated output. Route concept-only animation, formula, or proof explainers to manim-agent.
---

# Practical Course Producer

## Job

Turn a real tool workflow into a teachable, reviewable course video. The video is
the lesson: its scenes, demonstrations, narration, pauses, and checks must carry
the complete teaching sequence. Planning files are production intermediates,
not substitutes for the finished media.

Never fabricate hands-on evidence with `echo`, `Write-Host`, `print`, scripted
terminal text, or a long one-shot prompt presented as interactive work.

The product boundary is any workflow with a real starting state, observable
action, resulting state change, and verification. Read
`references/product-boundary.md` before accepting an unfamiliar course topic or
when the request might belong to Manim, deck generation, ordinary video editing,
or marketing media. A pure concept explainer is outside this Skill even if it
could be presented inside a fake terminal.

## Inputs

Collect or locate only what the requested phase needs:

- learning goal, audience, target duration, and language;
- the real workflow, repository, CLI, browser tool, or source artifacts;
- existing recordings, narration, slides, subtitles, or prior audit reports;
- output directory and any locked sections that must not change;
- optional voice, branding, or publishing constraints.

Do not request credentials in chat. Use existing authenticated sessions or
environment variables. Never write API keys, tokens, cookies, private recordings,
or raw model logs into the skill package or generated reports.

## Outputs

The primary deliverable is a versioned, publishable course video. Produce the
smallest set of intermediate artifacts needed to make that video reproducible:

1. Final media: a versioned course video plus short check clips when review is
   needed.
2. `lesson-plan.md`: the video's learning outcome, scene spine, and acceptance
   evidence.
3. `interaction-plan.md`: short user turns, expected tool actions, and why each
   turn exists.
4. `recording-checklist.md`: scenes, commands, files, failures, corrections, and
   retests that must be captured.
5. `narration.md`: spoken explanation aligned to observable actions.
6. `audit.md`: commands run, frame/audio checks, known issues, and verdict.

Use stable, descriptive filenames. Keep generated runs outside the installed
skill directory.

## Workflow

Keep one `course-project.json` as the production status source. Start from
`assets/course-project.json`, replace its placeholders, and keep every artifact
path relative to the project directory. Do not enter a later stage because a
draft video happens to exist.

### 1. Audit before planning

- Inspect the latest real artifacts, repository state, and previous audit.
- State what is confirmed, missing, locked, and unsafe to change.
- Confirm the requested final format, duration, aspect ratio, and publishing
  constraints before committing to a render plan.

### 2. Build the lesson spine

Design a small number of meaningful stages:

1. Explain the method or tool.
2. State the task and success evidence.
3. Create or run the first version.
4. Inspect files or output.
5. Show one real failure or weakness.
6. Give focused feedback and rerun.
7. Verify the final artifact with a real check.

Keep the method central. Treat the example as evidence, not the course topic.

Create `lesson-plan.md`, `interaction-plan.md`, `recording-checklist.md`, and
`narration.md`, then require the planning gate to pass:

```powershell
python scripts/validate_course_project.py path\to\course-project.json --gate plan
```

### 3. Plan real interaction

- Use short, natural user messages with one logical purpose each.
- Record what the tool actually returns; do not prewrite its response.
- Explain what was asked, why it was phrased that way, what changed, and what
  evidence proves the change.
- Keep useful mistakes. Cut only dead waiting after preserving enough reading
  time.

Read `references/recording-workflow.md` before recording a terminal, browser,
or AI coding session.

### 4. Record or collect evidence

- Prefer a browser-mirrored local terminal when foreground recording would
  disrupt the user's desktop.
- Enter interactive tools normally, then type messages inside the session.
- Capture file inspection, validator failure, repair, and retest when relevant.
- Stop if the real tool cannot run. Report the blocker instead of simulating it.

After the scene plan references actual source recordings, require the recording
gate to pass. Missing or empty recordings are a project blocker, not an editing
task:

```powershell
python scripts/validate_course_project.py path\to\course-project.json --gate record
```

Generate Chinese narration with Volcengine TTS HTTP Chunked v3 by default and
Edge TTS as the fallback. Set `VOLCENGINE_TTS_API_KEY` in the environment;
optionally override `VOLCENGINE_TTS_SPEAKER` and
`VOLCENGINE_TTS_RESOURCE_ID` together. Never put credentials in a project file
or command. If the key is missing or rejected, direct the user to
`https://console.volcengine.com/speech/new/setting/apikeys?projectName=default`
to obtain or replace it; do not ask them to paste it into chat. The primary
request enables provider timestamps, protects the
sentence start, and writes the actual provider and any fallback reason beside
the audio:

Protocol family: `https://www.volcengine.com/docs/6561/1719100?lang=zh`.
The offline adapter uses its HTTP Chunked counterpart at
`/api/v3/tts/unidirectional`.

```powershell
python scripts/synthesize_narration.py path\to\narration.md `
  --output path\to\audio\narration.mp3 `
  --timeline path\to\audio\narration.timeline.json
```

Use `--voice` only to change the Edge fallback voice. Use
`--fallback-provider none` when a project must fail closed instead of falling
back. A fallback is never silent: `requested_provider`, `provider`,
`fallback_used`, and `fallback_reason` are written to the timeline. If both
providers fail after bounded retries, stop at the narration blocker; never
accelerate speech.

Reference the generated timeline as `captions` in each narrated scene. Captions
must follow the spoken sentence boundaries and remain inside the safe lower
margin without covering the command or validation evidence being discussed.

### 5. Assemble in locked passes

- Keep every meaningful render versioned.
- Replace only the target region when earlier sections are locked.
- Do not accelerate narration to force alignment. Adjust scene duration or trim
  verified dead waiting.
- Use local zoom only on the content viewport; keep titles and course framing
  fixed.

When real source recordings are ready, read `references/scene-plan.md` and
advance the project through the render gate:

```powershell
python scripts/advance_course_project.py path\to\course-project.json --to render
```

The project runner checks the record gate, calls `scripts/build_course_video.py`,
updates `final_video` and `run_manifest` atomically, and checks the render gate.
Use the builder directly only when diagnosing an isolated scene plan. Do not use
either script to fabricate demonstrations or replace missing evidence.

Do not begin visual or audio polishing unless the runner reports that the render
gate passed.

Read `references/editing-audit.md` before editing or validating media.

### 6. Verify before delivery

Verification must match the claimed output:

- final video: it teaches the complete workflow without requiring the viewer to
  read the intermediate planning files;
- lesson plan: every stage has a learning purpose and observable evidence;
- interaction plan: every user turn is short, necessary, and testable;
- recording: commands and model/tool output are genuine and readable;
- media: inspect changed-region clips, representative frames, duration, audio,
  and stream hashes when claiming untouched regions stayed unchanged;
- final report: list exact artifacts, tests, remaining risks, and next action.

Do not call a project complete because files merely exist.

Generate `audit.md` and representative frames from the rendered project, then
require the final project gate to pass:

```powershell
python scripts/advance_course_project.py path\to\course-project.json --to release
```

The release transition requires the rendered duration to stay within 20% of the
project target, then records `ffprobe` structure, SHA-256, silence intervals,
tool versions, and three representative frames. These deterministic checks do
not replace human review of teaching accuracy, readability, or narration
alignment; record that verdict in the generated `audit.md` before delivery.

## Dependencies

- Planning and audit only: no external dependency.
- Media inspection/editing: `ffmpeg` and `ffprobe` on `PATH`.
- Browser-terminal recording: a local terminal bridge and an authenticated tool
  session chosen by the user.
- Default narration: Volcengine TTS HTTP Chunked v3 plus network access and
  `VOLCENGINE_TTS_API_KEY`. Obtain or replace a missing/rejected key at
  `https://console.volcengine.com/speech/new/setting/apikeys?projectName=default`.
  The packaged public default is
  `zh_female_vv_uranus_bigtts` with `seed-tts-2.0`; cloned voices must override
  both speaker and matching resource ID. Edge TTS is the packaged fallback;
  install it with `python -m pip install edge-tts`.
- Optional ASR, alternate TTS, or avatar services: user-provided access through
  environment configuration; never persist secrets.

If a dependency is missing, complete unaffected planning/audit work and report
the blocked phase precisely.

## Failure Rules

- Missing source evidence: do not invent a workflow; request or locate evidence.
- Tool or provider failure: preserve the real error and decide whether it teaches
  the workflow; never replace it with fake success output.
- Missing or rejected Volcengine key: report the environment variable and the
  official API Key console URL; use the configured Edge fallback or stop when
  fallback is disabled.
- Dirty repository: do not mix unrelated changes; use a clean worktree or a
  separate staging directory.
- Unclear alignment: inspect several consecutive frames and audio boundaries
  before editing.
- No measurable improvement: leave a verified no-op instead of polishing wording.

## Voice

For Chinese narration, use compact spoken language. Prefer observable actions
such as "我现在看文件" over abstract claims such as "形成闭环". When TTS
misreads a filename, use a natural spoken form such as "graph 文件".

## Maintainer Verification

From the repository root, run the strict skill validator and any bundled tests.
The package must contain no credentials, private source media, local caches, or
absolute paths. Script changes require a smoke test.

From the skill directory, run the deterministic media smoke tests with:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Run the portable end-to-end project smoke from any working directory with:

```powershell
python scripts/smoke_course_project.py
```

See `examples/verified-cli-workflow.md` for the public example and
`RELEASE_NOTES.md` for the packaged release scope and verification record.

## Release Exit Boundary

After automated tests, evals, security checks, and repository integration pass,
run exactly one fresh forward test on a practical topic not used during Skill
development. Start from a normal user request and do not reuse prepared media or
historical course scripts. Deliver the resulting video and audit for human
review, then stop autonomous iteration.

Treat explicit user approval such as "satisfied", "ready to publish", or "leave
it there" as the hard completion signal. If the user reports a blocking defect,
make only the requested correction and repeat the same acceptance case. Do not
switch topics, add speculative features, or continue polishing after approval.
