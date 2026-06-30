---
name: manim-agent
description: >-
  Use when Codex needs to create, run, review, debug, or package Manim Agent workflows for mathematical or technical explainer videos: Manim animations, narrated teaching videos, formula or proof visualization, concept explainers, render review, DashScope CosyVoice TTS, FFmpeg muxing, or the local gqy20/manim-agent CLI/Web pipeline. Trigger on requests such as "做一个 Manim 动画", "生成讲解视频", "把这个公式可视化", "做数学动画", "带配音", "渲染成 mp4", "检查 Manim Agent", or "包装/维护这个 manim-agent skill".
---

# Manim Agent

Use this skill to run the full Manim Agent production workflow, not a simplified one-off Manim snippet. The default local repository should be provided with `--repo <path-to-manim-agent>`; if it is missing, clone `https://github.com/gqy20/manim-agent.git` before running project commands.

## Operating Mode

1. Clarify the requested output only when needed: topic, target duration, audience, voice/TTS need, quality level, and final file path.
2. Run `scripts/check_manim_agent_env.py` before the first real render in a session, or whenever a failure suggests missing dependencies.
3. Prefer the CLI path for direct video delivery. Use the Web path only when the user asks for task history, SSE progress, browser UI, or backend persistence.
4. Preserve the repository pipeline: planning, implementation, render resolution/review, narration, TTS, and mux. Do not replace it with a handmade `scene.py` unless the user explicitly asks for a raw Manim scene.
5. Produce concrete artifacts: final MP4, generated scene/code location, logs or error summary, and the command used.

## Required Interfaces

- A language-model interface is required for normal pipeline runs. Manim Agent uses Claude Agent SDK to plan scenes and write or fix Manim code; Manim and FFmpeg alone are not enough.
- A working local runtime is required before generation: Python 3.12+, `uv`, Manim, FFmpeg, `claude-agent-sdk`, and `httpx`. Run `scripts/check_manim_agent_env.py` instead of guessing.
- The LLM interface can come from Claude Code local auth, official Anthropic credentials, or a compatible provider configured through `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_API_KEY`, and `ANTHROPIC_MODEL`.
- Use `scripts/configure_manim_provider.py` to print provider-specific env commands without exposing keys. It supports Aliyun DashScope/Bailian regular API, Aliyun Token Plan, Aliyun Coding Plan, Volcengine Ark regular API, and Volcengine Ark Coding Plan.
- For Aliyun and Volcengine, keep regular API keys and plan keys matched to their own Anthropic/Claude-compatible base URLs. Do not point Claude Agent SDK at a plain OpenAI-compatible route such as `/compatible-mode/v1` or `/api/v3` unless the provider console explicitly says it is Claude/Anthropic-compatible.
- Provider smoke tests should use the env printed by `configure_manim_provider.py`, including `MANIM_AGENT_FORCE_CLAUDE_SETTINGS=1`, so stale local Claude settings do not override the selected provider.
- If a requested Volcengine model alias returns `InvalidEndpointOrModel.NotFound` or `UnsupportedModel`, report that the endpoint/model is not enabled for the account and ask the user to create or choose an enabled Ark endpoint/model in the Volcengine console.
- If Phase 1 fails before rendering, check the LLM provider first: expired plan, invalid model name, missing auth token, or incompatible structured-output behavior.
- If provider calls work but rendering fails on `Tex` or `MathTex`, treat it as a local Manim/LaTeX dependency or generated-scene compatibility issue, not as an LLM credential failure.
- TTS is optional. Use `--no-tts` for smoke tests. For narrated output, configure DashScope CosyVoice with `DASHSCOPE_API_KEY`; do not expect the skill package to contain an API key.
- The speech route is Aliyun DashScope CosyVoice. Default model: `cosyvoice-v3-flash`; default voice: `longanyang`. The adapter downloads the returned audio URL and measures real duration before muxing.
- Database and R2 credentials are not required for direct CLI MP4 generation; they are only needed for the Web/backend persistence path.

## Reference Routing

- Read `references/repo-runtime.md` for installation, environment variables, CLI/Web commands, ports, and local paths.
- Read `references/pipeline-workflow.md` before running or explaining the end-to-end pipeline.
- Read `references/production-quality.md` before generating or reviewing teaching animation content.
- Read `references/recovery-and-review.md` when a render, structured output, TTS, mux, or frontend/backend task fails.

## Default CLI Pattern

From `<path-to-manim-agent>`:

```powershell
uv run python -m manim_agent "解释傅里叶变换的核心直觉" --target-duration 60 --quality medium --no-tts -o outputs/fourier.mp4
```

Use `--no-tts` for the first smoke run unless the user explicitly wants narration and a supported TTS key is available. For production narration:

```powershell
uv run python -m manim_agent "证明勾股定理" --target-duration 60 --quality high --voice longanyang --render-review -o outputs/pythagorean.mp4
```

## Delivery Rules

- State whether the run used no-TTS, TTS, BGM, render review, intro/outro, full render, or segment render.
- Never claim the video is ready until the MP4 path exists and is readable.
- If a dependency is missing, report the exact missing dependency and the next command to fix it.
- If a secret is provided in chat, use it only for the current run when necessary; do not write it into this skill, logs, examples, or user-visible output.
- If the user asks for a packaged skill or reusable workflow, update this skill rather than scattering notes into the repository.
- Do not expose API keys, database URLs, R2 credentials, or `.env` values in responses.

## Local Repo Awareness

The upstream repo already contains a production plugin at `plugins/manim-production/` with scene planning, scene building, layout safety, narration sync, render review, and intro/outro rules. Reuse those rules when working inside the repo. This Codex skill is the stable outer entrypoint: it decides when to invoke the repo, which path to run, what checks to perform, and what evidence to return.
