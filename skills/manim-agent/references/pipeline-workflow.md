# Pipeline Workflow

Use this file to preserve the full Manim Agent workflow.

## Main Flow

1. Convert the user's request into a structured teaching plan.
2. Build Manim scene code inside the task working directory.
3. Render the visual video.
4. Resolve real output files and optionally run render review.
5. Generate narration if TTS is enabled.
6. Synthesize voice with DashScope CosyVoice TTS.
7. Mux video, voice, optional subtitles, and optional BGM into the final MP4.
8. Return artifact paths and a short run summary.

Do not skip directly to writing Manim code for normal video requests. The repository's value is the structured pipeline and review loop.

## Phase Boundaries

Phase 1 planning:

- Input: user text, target duration, preset, quality, render mode.
- Output: structured `build_spec`.
- No file reads, writes, shell commands, or rendering.
- If structured output fails, stop early; do not invent a free-form replacement.

Phase 2 implementation:

- Input: accepted `build_spec`.
- Output: scene code, rendered artifact, `PipelineOutput`.
- Expected default file: `scene.py`.
- Expected main class: `GeneratedScene`.
- Fix implementation failures before redesigning the lesson.

Phase 3 render resolve/review:

- Always verify real video paths.
- `--render-review` enables independent frame review.
- Default code path may skip independent review for speed, but still resolves files.
- If review is enabled and returns blocking issues, report failure and suggested edits.

Phase 3.5 narration:

- Generate narration aligned to the accepted visual beats.
- Narration should describe what is on screen now, not read ahead.

Phase 4 TTS:

- Requires `DASHSCOPE_API_KEY` unless `--no-tts` is used.
- Default model: `cosyvoice-v3-flash`.
- Default voice: `longanyang`.
- Default route: DashScope CosyVoice speech synthesis.
- Download the returned audio URL and measure real audio duration before beat-level alignment.

Phase 5 mux:

- Combine visual video, voice, optional subtitle timing, optional BGM, and intro/outro if requested.
- Final success requires the target MP4 file to exist.

## Choosing Runtime Path

Use CLI when:

- The user wants a video artifact.
- The user gives a topic and output path.
- The task is a one-off generation or debug run.

Use Web mode when:

- The user wants a dashboard, task history, or progress stream.
- The user asks to inspect backend/frontend behavior.
- The user wants persisted task records or R2 upload behavior.

Use raw Manim only when:

- The user explicitly asks for only `scene.py`.
- The user asks to debug a specific Manim script.
- The repository pipeline is unavailable and the user accepts a degraded path.

## Output Evidence

For completed runs, report:

- Command used.
- Output MP4 absolute path.
- Whether TTS, BGM, render review, intro/outro, and segment mode were used.
- Relevant task directory or generated code path.
- Any skipped feature and why.

For failed runs, report:

- Failing phase.
- Exact command or subsystem.
- Short stderr/log excerpt.
- Missing dependency or contract mismatch.
- Next concrete fix.

## Artifact Hygiene

- Put generated outputs under the repo `outputs/` directory or a user-specified project directory.
- Do not write generated task files into the repo root unless the repo command does so intentionally.
- Do not expose `.env`, API keys, database URLs, or R2 credentials.
- Do not delete generated artifacts unless the user asks for cleanup.
