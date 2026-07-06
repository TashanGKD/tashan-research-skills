<div align="center">

# Tashan Research Skills

**A bilingual, self-contained skill library for AI-assisted academic research**

*Literature evidence · Research ideation · Research expression · Collaboration memory · Tool evaluation*

[English](README.md) · [简体中文](README.zh-CN.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/Skills-17-2E74B5.svg)](skills/README.md)
[![Modules](https://img.shields.io/badge/Modules-5-0B2545.svg)](#skill-matrix)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

<img src="assets/research-skills-overview.png" alt="Tashan Research Skills overview" width="720" />

</div>

---

## Overview

Tashan Research Skills hosts **17 production-grade agent skills** that cover the daily jobs of a working researcher: finding and verifying literature, shaping ideas into testable designs, turning results into papers, figures, slides, and videos, and keeping long-term collaboration context. Every skill is a self-contained directory with a `SKILL.md` entrypoint plus its own scripts, references, templates, and tests.

This project is supported by the **Panshi AI4Science Ecosystem and Application Model Research Project**.

### Design principles

- **One skill, one research job** — each skill owns a single, clearly bounded workflow.
- **Evidence over eloquence** — skills track sources, mark evidence boundaries, and refuse to overclaim.
- **Deterministic where possible** — parsing, randomization, packaging, and validation are plain scripts with tests; model judgment is reserved for reasoning.
- **No secrets in the repo** — all credentials come from environment variables at runtime.

## Skill Matrix

### Literature evidence

| Skill | Path | What it does |
| --- | --- | --- |
| Paper Search | [`skills/giiisp-paper-search-apis`](skills/giiisp-paper-search-apis/SKILL.md) | Search Giiisp and open paper sources, then return verifiable candidate papers. |
| Deep Research | [`skills/sci-employee-deep-research`](skills/sci-employee-deep-research/SKILL.md) | Break down a research question, collect evidence, and produce a traceable research report. |
| Thesis Audit Reviewer | [`skills/thesis-audit-reviewer`](skills/thesis-audit-reviewer/SKILL.md) | Audit thesis or manuscript claims, evidence, references, methods, and completion gates. |

### Research ideation

| Skill | Path | What it does |
| --- | --- | --- |
| Scispark | [`skills/scispark`](skills/scispark/SKILL.md) | Generate evidence-tracked research ideas and testable hypotheses from papers or keywords. |
| Research Baseline Builder | [`skills/research-baseline-builder`](skills/research-baseline-builder/SKILL.md) | Translate a scientific question into data inputs, outputs, baselines, and metrics. |
| Experiment Design | [`skills/experiment-design`](skills/experiment-design/SKILL.md) | Design statistically sound experiments before data collection: design types, randomization, sample size, power, and analysis plans. |

### Research expression

| Skill | Path | What it does |
| --- | --- | --- |
| Scientific Humanization | [`skills/scientific-humanization`](skills/scientific-humanization/SKILL.md) | Rewrite Chinese scientific text so it sounds natural while preserving facts and evidence boundaries. |
| Academic Writing | [`skills/academic-writing`](skills/academic-writing/SKILL.md) | Draft, review, revise, and submit academic work: manuscripts, peer review, rebuttals, grants, and submission materials. |
| Scientific Image Generation | [`skills/giiisp-scientific-image-generation`](skills/giiisp-scientific-image-generation/SKILL.md) | Turn paper paragraphs, mechanisms, and experiment flows into scientific image briefs and runs. |
| Visual Deck Builder | [`skills/visual-deck-builder`](skills/visual-deck-builder/SKILL.md) | Build image-model-driven PPT decks from topics, papers, reports, notes, or style references. |
| Manim Agent | [`skills/manim-agent`](skills/manim-agent/SKILL.md) | Create, review, and package mathematical or technical explainer videos. |

### Collaboration memory

| Skill | Path | What it does |
| --- | --- | --- |
| PaperCheck | [`skills/papercheck`](skills/papercheck/SKILL.md) | Audit citations, references, formats, and context support in academic papers. |
| Cognitive Profile | [`skills/cognitive-profile`](skills/cognitive-profile/SKILL.md) | Maintain a reviewable research/user preference profile for long-term collaboration. |
| Research Dream | [`skills/research-dream`](skills/research-dream/SKILL.md) | Consolidate daily research conversations into long-term research-avatar memory files. |
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

Skills read secrets from environment variables at runtime and degrade gracefully when a credential is absent (dry-run, local fallback, or a clear blocker report).

| Environment variable | Needed by | Purpose |
| --- | --- | --- |
| `GIIISP_AUTH_TOKEN` | Scientific Image Generation, Visual Deck Builder, Paper Search | Giiisp API access (image generation, search) |
| `DASHSCOPE_API_KEY` | Manim Agent, MCP-CriticAgent | CosyVoice TTS, LLM-driven smart tests |
| `MINERU_API_TOKEN` | Thesis Audit Reviewer | Optional MinerU online PDF parsing (local fallback exists) |
| `OPENAI_API_KEY` | Visual Deck Builder, MCP-CriticAgent | Alternative image / test backends |
| `ANTHROPIC_AUTH_TOKEN` | Manim Agent | Claude-compatible LLM route for scene generation |

## Repository Layout

```text
.
├── assets/                  # Public images used by docs
├── docs/                    # Human-readable package docs (Chinese overview)
├── skills/                  # 17 skill directories, each with a SKILL.md entrypoint
├── .github/                 # Issue and PR templates
├── manifest.yml             # Machine-readable skill index (id / category / entrypoint)
├── CONTRIBUTING.md          # Collaboration rules
├── SECURITY.md              # Secret and vulnerability policy
├── LICENSE                  # MIT License
├── README.md                # English README
└── README.zh-CN.md          # Chinese README
```

## Engineering Standards

This repository is kept easy to review and hard to rot:

- Keep each skill focused on one research job.
- Keep reusable scripts inside the owning skill's `scripts/` directory.
- Prefer Markdown references and structured manifests over large binary-only documentation.
- Do not commit generated run outputs, raw model logs, private papers, credentials, or local caches.
- For changes to scripts, include a smoke test or a documented manual verification command.
- For changes to skill behavior, update the related `SKILL.md` and any referenced docs in the same PR.

## Security

Do not put API keys, access tokens, bind keys, cookies, private SSH keys, or service credentials in this repository. Skills that need external services must read secrets from environment variables or local user configuration. See [`SECURITY.md`](SECURITY.md) for the full policy and how to report a vulnerability.

## Contributing

Contributions are welcome — new skills, fixes, tests, and docs. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) first; the short version is: one skill per PR scope, tests or a verification command for script changes, and `SKILL.md` updated together with behavior changes.

## Authors and Support

**Authors and contributors**

Qiao Han (乔晗) · Zhu Xiaomo (朱晓墨) · Yu-Yang Li · Cai Anping (蔡安平) · Wang Rui (王瑞) · Fang Zerui (房泽锐) · OpenAI Codex-assisted development contributors

**Supporting project**

Panshi AI4Science Ecosystem and Application Model Research Project

## License

Released under the [MIT License](LICENSE).
