# Repo Runtime

Use this file for installation, environment checks, commands, and runtime surfaces.

## Source

- Upstream: `https://github.com/gqy20/manim-agent.git`
- Default local repo: `<path-to-manim-agent>`
- Python package: `manim-agent`
- Python entrypoint: `python -m manim_agent`
- Core code: `src/manim_agent/`
- Runtime plugin: `plugins/manim-production/`
- Backend: `backend/`
- Frontend: `frontend/`

If the repo is missing:

```powershell
git clone https://github.com/gqy20/manim-agent.git "<path-to-manim-agent>"
```

If the user asks for the latest upstream behavior, run `git -C "<path-to-manim-agent>" pull --ff-only` and inspect the changed files before making claims.

## Dependencies

Required for CLI video generation:

- Python 3.12+
- `uv`
- Manim 0.20.1+
- FFmpeg in `PATH`
- Claude Agent SDK access, normally through local Claude auth, official Anthropic credentials, or an Anthropic-compatible provider

Required Python packages in the repo environment:

- `claude-agent-sdk`
- `manim`
- `httpx`
- `fastapi`, `uvicorn`, `asyncpg`, `psycopg[binary]`, `boto3` when using Web/backend persistence

Required for narrated production:

- Aliyun DashScope CosyVoice TTS route: `DASHSCOPE_API_KEY`, endpoint `https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer`, default model `cosyvoice-v3-flash`, default voice `longanyang`

Required for Web backend persistence:

- `DATABASE_URL`
- Optional R2 variables: `R2_BUCKET_NAME`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_PUBLIC_URL`

Check environment:

```powershell
python ".\scripts\check_manim_agent_env.py" --repo "<path-to-manim-agent>"
```

## Install

From the repo:

```powershell
uv sync --group dev
uv pip install -e .
```

Fallback:

```powershell
python -m pip install -e ".[dev]"
```

FFmpeg is a system dependency, not just a Python package. On Windows it must be discoverable as `ffmpeg` in `PATH`; a local wrapper or copied `ffmpeg.exe` under `.codex-tools/` is acceptable for smoke tests but should be made explicit in the run environment.

## Language Model Interface

Normal CLI runs need an LLM provider because the repository calls Claude Agent SDK during Phase 1 planning and Phase 2 implementation. If the SDK cannot call a model, the pipeline stops before Manim rendering.

Use the profile helper to map a provider key that is already in an environment variable into the Claude Agent SDK env contract. The helper prints commands only; it never prints key values.

```powershell
# Aliyun regular DashScope/Bailian API
python ".\scripts\configure_manim_provider.py" --provider aliyun --route regular --format powershell

# Aliyun plan routes
python ".\scripts\configure_manim_provider.py" --provider aliyun --route token-plan --format powershell
python ".\scripts\configure_manim_provider.py" --provider aliyun --route coding-plan --format powershell

# Volcengine Ark regular API and Coding Plan
python ".\scripts\configure_manim_provider.py" --provider volcengine --route regular --format powershell
python ".\scripts\configure_manim_provider.py" --provider volcengine --route coding-plan --format powershell
```

Provider profiles:

| Provider route | Base URL | Preferred source key env | Default model |
| --- | --- | --- | --- |
| Aliyun regular | `https://dashscope.aliyuncs.com/apps/anthropic` | `ALIYUN_DASHSCOPE_API_KEY` or `DASHSCOPE_API_KEY` | `qwen3.7-plus` |
| Aliyun Token Plan | `https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic` | `ALIYUN_TOKEN_PLAN_API_KEY` | `qwen3.7-plus` |
| Aliyun Coding Plan | `https://coding.dashscope.aliyuncs.com/apps/anthropic` | `ALIYUN_CODING_PLAN_API_KEY` | `qwen3.7-plus` |
| Volcengine Ark regular | `https://ark.cn-beijing.volces.com/api/compatible` | `ARK_API_KEY` or `VOLCENGINE_API_KEY` | `deepseek-v3-2-251201` |
| Volcengine Ark Coding Plan | `https://ark.cn-beijing.volces.com/api/coding` | `ARK_API_KEY` or `VOLCENGINE_API_KEY` | `ark-code-latest` |

If the provider console lists a different current model or Claude-compatible base URL, keep the same profile but override the current values:

```powershell
python ".\scripts\configure_manim_provider.py" --provider volcengine --route regular --base-url "<console Claude-compatible base URL>" --model "<console model>" --format powershell
```

Do not mix key families and endpoints. A normal DashScope/Bailian key, a Token Plan key, a Coding Plan key, and a Volcengine Ark key may all look similar in examples, but their valid base URLs and model lists are different.

Check these first when Phase 1 fails:

```powershell
claude --version
$env:ANTHROPIC_BASE_URL
$env:ANTHROPIC_MODEL
```

Known failure patterns:

- `模型不存在`: the configured `ANTHROPIC_MODEL` is not accepted by the current provider.
- `plan 套餐已到期` or `429`: provider account or subscription is unavailable.
- No structured output: provider/model may not support the SDK structured-output contract used by the pipeline.

The TTS key cannot replace this LLM interface. It only affects narration synthesis after the visual video has already been planned and rendered.

Direct `anthropic.Anthropic(...)` calls and Manim Agent's `claude_agent_sdk` path are not identical. The direct SDK only uses the values passed in code; `claude_agent_sdk` starts Claude Code CLI, which can also read `~/.claude/settings.json`. If local Claude settings point to another provider, pass explicit settings or set `MANIM_AGENT_FORCE_CLAUDE_SETTINGS=1` in this repo's patched runtime.

## TTS Route

Default DashScope CosyVoice TTS route:

```powershell
$env:DASHSCOPE_API_KEY = "<secret>"
```

The repository adapter calls DashScope CosyVoice, downloads the returned audio URL to `audio.mp3`, and measures real audio duration with FFmpeg/ffprobe before beat-level alignment. CosyVoice is the normal narration route for this skill.

## CLI Commands

Silent smoke run:

```powershell
uv run python -m manim_agent "讲解二叉树的遍历方式" --no-tts --quality medium --target-duration 60 -o outputs/tree.mp4
```

Narrated production:

```powershell
uv run python -m manim_agent "解释傅里叶变换的原理" --voice longanyang --quality high --target-duration 60 -o outputs/fourier.mp4
```

Strict visual review:

```powershell
uv run python -m manim_agent "证明勾股定理" --render-review --quality high --target-duration 60 -o outputs/proof.mp4
```

Segment rendering:

```powershell
uv run python -m manim_agent "解释梯度下降" --render-mode segments --target-duration 180 -o outputs/gradient.mp4
```

Optional BGM:

```powershell
uv run python -m manim_agent "解释神经网络反向传播" --bgm-enabled --bgm-volume 0.10 -o outputs/backprop.mp4
```

## CLI Options To Remember

- `text`: natural language video requirement
- `-o, --output`: output MP4 path
- `--voice`: CosyVoice voice ID; default `longanyang`
- `--model`: CosyVoice TTS model; default `cosyvoice-v3-flash`
- `--quality`: `high`, `medium`, or `low`
- `--no-tts`: skip TTS
- `--bgm-enabled`, `--bgm-prompt`, `--bgm-volume`
- `--cwd`: working directory
- `--prompt-file`: custom prompt file
- `--max-turns`: default 80 in current code
- `--target-duration`: one of 30, 60, 180, 300
- `--render-mode`: `full` or `segments`
- `--intro-outro`
- `--intro-outro-backend`: `revideo` or `manim`
- `--render-review`: enable independent visual review

## Web Runtime

Use Web mode only when the user needs task management, browser UI, history, or SSE status.

Backend:

```powershell
make dev-backend
```

Frontend:

```powershell
make dev-frontend
```

Default ports:

- Backend: `127.0.0.1:8471`
- Frontend: `localhost:3147`

If the frontend port is busy:

```powershell
make dev-frontend FE_PORT=3148
```

## Tests And Checks

```powershell
uv run pytest tests/ -v
uv run pytest backend/tests/ -v
uv run ruff check src/ backend/ tests/
uv run ruff format src/ backend/ tests/
```

Some tests depend on PostgreSQL, Manim, FFmpeg, or external APIs. If a test cannot run because a service key is absent, report that explicitly instead of treating it as code failure.
