# Recovery And Review

Use this file when the pipeline fails or the output quality is uncertain.

## First Triage

Identify the failing layer:

- Environment: Python, uv, Manim, FFmpeg, API keys, repo missing.
- LLM provider: Claude Agent SDK auth, model name, provider plan, structured-output support.
- Planning: structured `build_spec` missing or invalid.
- Implementation: agent wrote invalid code, wrong file, wrong class, hook rejection.
- Render: Manim command failed, missing asset, TeX/font issue, frame overflow.
- Review: render review blocked or could not read frames.
- TTS: DashScope key, CosyVoice voice/model, timestamp mismatch.
- Mux: FFmpeg failed, missing audio/video, duration mismatch.
- Web: backend, frontend, database, SSE, R2 upload.

## Environment Failures

Run:

```powershell
python ".\scripts\check_manim_agent_env.py" --repo "<path-to-manim-agent>"
```

If `uv` is missing, install or use `python -m pip install -e ".[dev]"`.

If `ffmpeg` is missing, install it and confirm `ffmpeg -version`.

If Manim is missing, run:

```powershell
uv sync --group dev
uv pip install -e .
```

If TTS fails and the task does not require narration, rerun with `--no-tts`. If narration is required, fix the DashScope CosyVoice TTS route first.

## LLM Provider Failures

The pipeline needs a working Claude Agent SDK model call before it can render anything. If Phase 1 fails with an SDK child-process error, inspect the latest Claude session log under:

```text
%USERPROFILE%\.claude\projects\
```

Typical fixes:

- Invalid model name: set `ANTHROPIC_MODEL` to a model accepted by the configured provider.
- Expired provider plan or quota: renew or switch the provider before retrying.
- Wrong base URL/token pair: align `ANTHROPIC_BASE_URL` with the matching auth token.
- Structured output incompatibility: use a provider/model known to work with Claude Agent SDK structured output.

For provider setup, prefer the helper so the key value stays in its source env var:

```powershell
python ".\scripts\configure_manim_provider.py" --provider aliyun --route regular --format powershell
python ".\scripts\configure_manim_provider.py" --provider volcengine --route regular --format powershell
```

For Aliyun DashScope, Claude Agent SDK should use the Anthropic-compatible endpoint:

```powershell
$env:ANTHROPIC_BASE_URL = "https://dashscope.aliyuncs.com/apps/anthropic"
$env:ANTHROPIC_MODEL = "qwen3.7-plus"
```

Do not use the OpenAI-compatible endpoint `https://dashscope.aliyuncs.com/compatible-mode/v1` for this repo's Claude Agent SDK path.

If using Token Plan or Coding Plan, use the matching plan endpoint instead of the normal DashScope endpoint:

```powershell
# Token Plan
$env:ANTHROPIC_BASE_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic"

# Coding Plan
$env:ANTHROPIC_BASE_URL = "https://coding.dashscope.aliyuncs.com/apps/anthropic"
```

For Volcengine Ark, distinguish the regular Claude-compatible route from the Coding Plan route:

```powershell
# Regular Ark API route for Claude/Anthropic-compatible tools
$env:ANTHROPIC_BASE_URL = "https://ark.cn-beijing.volces.com/api/compatible"
$env:ANTHROPIC_MODEL = "doubao-seed-code-preview-latest"

# Ark Coding Plan route
$env:ANTHROPIC_BASE_URL = "https://ark.cn-beijing.volces.com/api/coding"
$env:ANTHROPIC_MODEL = "ark-code-latest"
```

If the Ark console shows a newer Claude-compatible base URL or model, pass it through `configure_manim_provider.py --base-url ... --model ...` instead of editing secrets into docs.

`model not found`, `模型不存在`, or `Incorrect API key provided` often means the key family and base URL are mismatched, not that Manim failed.

If a direct `anthropic.Anthropic(...)` smoke test works but `claude_agent_sdk` still calls the wrong provider, inspect `~/.claude/settings.json`; Claude Code CLI can load provider env from settings unless explicitly overridden.

Do not treat these as Manim render failures. They occur before `scene.py` is generated.

## Structured Output Failures

Do not patch around the schema by inventing a free-form plan. Report:

- Which phase expected structured output.
- Whether a raw structured output was present.
- The validation error if available.
- Whether the repo changed recently.

Then inspect:

- `src/manim_agent/schemas/`
- `src/manim_agent/pipeline_phases12.py`
- `src/manim_agent/dispatcher.py`
- Relevant tests under `tests/test_pipeline_*` and `tests/test_output_schema.py`

## Render Failures

Check in this order:

1. Correct working directory.
2. `scene.py` exists.
3. `GeneratedScene` exists, or the command uses the actual class name.
4. Manim can import all dependencies.
5. TeX or font errors are real environment errors, not scene logic errors.
6. Output file path exists after render.
7. Frame is not blank, cropped, or overloaded.

If a hook blocks writes outside the task directory, do not keep trying similar absolute paths. Move all generated files into the task directory.

## Review Failures

If `--render-review` blocks the run, treat it as real until checked:

- Open or inspect sampled frames.
- Check for text overlap, empty frame, unreadable math, off-screen objects, or wrong visual sequence.
- Fix the scene or rerun with a narrower prompt.

Only disable render review when speed matters more than quality and the user accepts that tradeoff.

## TTS And Mux Failures

For TTS:

- Confirm `DASHSCOPE_API_KEY` exists without printing it.
- Confirm requested CosyVoice voice and model are supported in DashScope.
- Retry once if it is a transient network failure.
- Use `--no-tts` only if the user accepts a silent output.
- Use the DashScope CosyVoice adapter: model such as `cosyvoice-v3-flash`, voice such as `longanyang`.
- Confirm the returned audio URL can be downloaded and real duration can be measured; the beat alignment pipeline depends on real audio duration.

For mux:

- Confirm FFmpeg is available.
- Confirm visual MP4 and audio file paths exist.
- Check duration mismatch.
- Reduce BGM volume or disable BGM if mix fails.

## Web Failures

Use Web mode only when needed.

Backend checks:

```powershell
make dev-backend
uv run pytest backend/tests/ -v
```

Frontend checks:

```powershell
make dev-frontend
cd frontend
npm test
```

If database is missing, report `DATABASE_URL` requirement. Do not fake persisted task behavior with local-only CLI output.

## Regression Checks

For code changes in the repo:

```powershell
uv run pytest tests/ -v
uv run pytest backend/tests/ -v
uv run ruff check src/ backend/ tests/
```

For skill changes:

```powershell
python "<path-to-skill-creator>\scripts\quick_validate.py" "."
```
