<div align="center">

# Tashan Research Skills

**A bilingual agent skill library for research work**

*Literature evidence · Research ideation · Research expression · Collaboration memory · Tool evaluation*

[简体中文](README.md) · [English](README.en.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/Skills-19-2E74B5.svg)](skills/README.md)
[![Modules](https://img.shields.io/badge/Modules-5-0B2545.svg)](#skill-matrix)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

<img src="assets/research-skills-overview.png" alt="Tashan Research Skills overview" width="720" />

</div>

---

## Overview

This repository holds 19 research agent skills we built ourselves, organized into five groups: literature evidence, research ideation, research expression, collaboration memory, and tool evaluation. Each skill is one folder with a `SKILL.md` entrypoint; its scripts, templates, and tests sit in the same directory. Copy a folder into your agent's skills directory and it is ready to use.

The project is supported by the **Panshi AI4Science Ecosystem and Application Model Research Project**.

## Scientific Skill / MCP Discovery

[`find-science-skills`](skills/find-science-skills/SKILL.md) finds research Skills or MCPs for a concrete task. The host model identifies the resource type, research domain, research stage, and functional role, then invokes a deterministic, standard-library-only filter to narrow the catalog. It requires no backend service or API key.

When no resource type is specified, discovery defaults to Skills. Use MCP-only search when requested, and `--resource all` only when the user explicitly asks for both resource types.

The static catalogs currently contain 1,391 Skills and 5,643 active research MCPs across a shared taxonomy of 9 top-level domains, 42 subdomains, 5 research stages, and 17 function groups. Domain and stage define the retrieval boundary; function can be either a ranking preference or a strict filter. Results remain candidates for semantic review rather than a claim that catalog order equals relevance. The host recommends only resources whose research object and expected output both match directly, and reports a catalog gap when none do.

```powershell
# Inspect the supported taxonomy
python .\skills\find-science-skills\scripts\filter_science_resources.py --list-dimensions

# Inspect functions available for a domain and stage
python .\skills\find-science-skills\scripts\filter_science_resources.py `
  --domain 生命科学 --stage 分析验证 --list-functions

# Search Skills and MCPs together
python .\skills\find-science-skills\scripts\filter_science_resources.py `
  --resource all --domain 生命科学 --stage 分析验证 `
  --function 数据处理 --strict-function --json

# Apply strict filtering and return machine-readable output
python .\skills\find-science-skills\scripts\filter_science_resources.py `
  --resource mcp `
  --domain 生命科学 --subdomain 生物信息学 --stage 分析验证 `
  --function 数据处理 --strict-function --json
```

See [`skills/find-science-skills/SKILL.md`](skills/find-science-skills/SKILL.md) for the decision rules, readiness states, and response contract.

## Skill Matrix

### Literature evidence

| Skill | Path | What it does |
| --- | --- | --- |
| Find Science Skill / MCP | [`skills/find-science-skills`](skills/find-science-skills/SKILL.md) | Filter 1,391 research Skills and 5,643 active research MCPs by domain, research stage, and functional role while preserving source and readiness metadata for host-model review. |
| Paper Search | [`skills/giiisp-paper-search-apis`](skills/giiisp-paper-search-apis/SKILL.md) | Search Giiisp and open paper sources, then return verifiable candidate papers. |
| Deep Research | [`skills/sci-employee-deep-research`](skills/sci-employee-deep-research/SKILL.md) | Break down a research question, collect evidence, and produce a traceable research report. |
| Thesis Audit Reviewer | [`skills/thesis-audit-reviewer`](skills/thesis-audit-reviewer/SKILL.md) | Audit thesis or manuscript claims, evidence, references, methods, and completion gates. |

### Research ideation

| Skill | Path | What it does |
| --- | --- | --- |
| Scispark | [`skills/scispark`](skills/scispark/SKILL.md) | Generate evidence-tracked research ideas and testable hypotheses from papers or keywords. |
| Research Baseline Builder | [`skills/research-baseline-builder`](skills/research-baseline-builder/SKILL.md) | Translate a scientific question into data inputs, outputs, baselines, and metrics. |
| Experiment Design | [`skills/experiment-design`](skills/experiment-design/SKILL.md) | Design statistically sound experiments before data collection: design types, randomization, sample size, power, and analysis plans. |
| Statistical Analysis | [`skills/statistical-analysis`](skills/statistical-analysis/SKILL.md) | Run the locked analysis plan after data collection: tests, effect sizes, confidence intervals, assumption checks, and multiplicity correction. |

### Research expression

| Skill | Path | What it does |
| --- | --- | --- |
| Scientific Humanization | [`skills/scientific-humanization`](skills/scientific-humanization/SKILL.md) | Rewrite Chinese scientific text so it sounds natural while preserving facts and evidence boundaries. |
| Academic Writing | [`skills/academic-writing`](skills/academic-writing/SKILL.md) | Draft, review, revise, and submit academic work: manuscripts, peer review, rebuttals, grants, and submission materials. |
| Scientific Image Generation | [`skills/giiisp-scientific-image-generation`](skills/giiisp-scientific-image-generation/SKILL.md) | Turn paper paragraphs, mechanisms, and experiment flows into scientific image briefs and runs. |
| Visual Deck Builder | [`skills/visual-deck-builder`](skills/visual-deck-builder/SKILL.md) | Build image-model-driven PPT decks from topics, papers, reports, notes, or style references. |
| Manim Agent | [`skills/manim-agent`](skills/manim-agent/SKILL.md) | Create, review, and package mathematical or technical explainer videos. |
| Practical Course Producer | [`skills/practical-course-producer`](skills/practical-course-producer/SKILL.md) | Turn tool workflows with observable state changes and real verification into reproducible practical course videos. |

### Collaboration memory

| Skill | Path | What it does |
| --- | --- | --- |
| PaperCheck | [`skills/papercheck`](skills/papercheck/SKILL.md) | Audit citations, references, formats, and context support in academic papers. |
| Cognitive Profile | [`skills/cognitive-profile`](skills/cognitive-profile/SKILL.md) | Maintain a reviewable research/user preference profile with built-in dream-style consolidation. The optional Dream layer lives in [`skills/research-dream`](skills/research-dream/SKILL.md) (companion install, not listed separately). |
| World Threads Entry | [`skills/world-threads-entry`](skills/world-threads-entry/SKILL.md) | Connect TopicLab / 他山世界 / OpenClaw world-thread workflows. |

### Tool evaluation

| Skill | Path | What it does |
| --- | --- | --- |
| MCP-CriticAgent | [`skills/mcp-criticagent`](skills/mcp-criticagent/SKILL.md) | Deploy, test, and score MCP servers and tools: protocol checks, smart tests, and repository health. |
| Skill-CriticAgent | [`skills/skill-criticagent`](skills/skill-criticagent/SKILL.md) | Evaluate Agent Skills for spec compliance, security, behavior uplift, and trigger quality before installing. |

See [`docs/skill-package-overview.md`](docs/skill-package-overview.md) for the Chinese package overview and [`skills/README.md`](skills/README.md) for the machine-readable index.

## Getting Started

Each skill is self-contained: start from its `SKILL.md`, then follow the referenced `scripts/`, `references/`, `templates/`, or `assets/` in the same folder.

**1. Clone the repository**

```powershell
git clone https://github.com/TashanGKD/tashan-research-skills.git
cd tashan-research-skills
Get-ChildItem .\skills -Recurse -Filter SKILL.md
```

**2. Install a skill into your agent runtime**

```powershell
# Codex (Windows)
Copy-Item -Recurse .\skills\papercheck "$env:USERPROFILE\.codex\skills\papercheck"

# Claude Code / Cursor and other SKILL.md-compatible runtimes:
# copy the skill folder into the runtime's skills directory.
```

Replace `papercheck` with the skill folder you want. Skills have no cross-dependencies, so you can install any subset.

**3. Configure credentials (only if the skill needs them)**

Skills read secrets from environment variables at runtime. Missing a key is fine: some skills switch to dry-run, some fall back to local processing, and when a step truly cannot run they report exactly where it blocked instead of faking output.

| Environment variable | Needed by | Purpose | Where to apply |
| --- | --- | --- | --- |
| `GIIISP_AUTH_TOKEN` | Scientific Image Generation, Visual Deck Builder, Paper Search | Giiisp API access (image generation, search) | [giiisp.com](https://giiisp.com/#/mcp/authenticate) |
| `DASHSCOPE_API_KEY` | Manim Agent, Scientific Image Generation, Visual Deck Builder, MCP-CriticAgent | Scene generation, Qwen VLM review, CosyVoice TTS, smart tests | [Aliyun Model Studio](https://help.aliyun.com/zh/model-studio/get-api-key) |
| `MINERU_API_TOKEN` | Thesis Audit Reviewer | Optional MinerU online PDF parsing (local fallback exists) | [mineru.net](https://mineru.net/apiManage/token) |

Manim Agent runs on Aliyun Model Studio's Claude Code compatible route: scene generation and CosyVoice TTS reuse the same `DASHSCOPE_API_KEY`; no separate Anthropic key is needed.

## Repository Layout

```text
.
├── assets/                  # Public images used by docs
├── docs/                    # Human-readable package docs (Chinese overview)
├── skills/                  # Skill directories, each with a SKILL.md entrypoint
├── .github/                 # Issue and PR templates
├── manifest.yml             # Machine-readable skill index (id / category / entrypoint)
├── CONTRIBUTING.md          # Collaboration rules
├── SECURITY.md              # Secret and vulnerability policy
├── LICENSE                  # MIT License
├── README.md                # Chinese README (default)
└── README.en.md             # English README
```

## Authors and Support

**Authors and contributors**

Qiao Han (乔晗) · Zhu Xiaomo (朱晓墨) · Yu-Yang Li · Cai Anping (蔡安平) · Wang Rui (王瑞) · Fang Zerui (房泽锐)

**Supporting project**

Panshi AI4Science Ecosystem and Application Model Research Project

## License

Released under the [MIT License](LICENSE).
