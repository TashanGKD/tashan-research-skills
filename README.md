# Tashan Research Skills

[中文 README](README.zh-CN.md)

Tashan Research Skills is a bilingual academic research skills repository for literature review, evidence checking, research ideation, scientific writing, slides, figures, citation audit, and long-term research workflow collaboration.

This project is supported by the **Panshi AI4Science Ecosystem and Application Model Research Project**.

![Tashan Research Skills overview](assets/research-skills-overview.png)

## Overview

The repository currently includes **12 skills**. Each skill is a self-contained workflow directory with a `SKILL.md` entrypoint and, when needed, supporting scripts, references, templates, examples, or assets.

The skills are grouped around four practical research jobs:

| Module | What it supports | Skills |
| --- | --- | --- |
| Literature evidence | Paper search, evidence retrieval, claim tracing, manuscript audit, and evidence boundary checks. | Paper Search, Deep Research, Thesis Audit Reviewer |
| Research ideation | Turning topics, paper sets, or early questions into hypotheses, mechanisms, data tasks, baselines, and evaluation plans. | Scispark, Research Baseline Builder |
| Research expression | Improving scientific writing and producing figures, slides, and technical explainer videos. | Scientific Humanization, Scientific Image Generation, Visual Deck Builder, Manim Agent |
| Collaboration memory | Citation compliance, preference memory, and long-running research collaboration workflows. | PaperCheck, Cognitive Profile, World Threads Entry |

## Included Skills

| Skill | Path | Purpose |
| --- | --- | --- |
| Paper Search | [`skills/giiisp-paper-search-apis`](skills/giiisp-paper-search-apis/SKILL.md) | Search Giiisp and open paper sources, then return verifiable candidate papers. |
| Deep Research | [`skills/sci-employee-deep-research`](skills/sci-employee-deep-research/SKILL.md) | Break down a research question, collect evidence, and produce a traceable research report. |
| Thesis Audit Reviewer | [`skills/thesis-audit-reviewer`](skills/thesis-audit-reviewer/SKILL.md) | Audit thesis or manuscript claims, evidence, references, methods, and completion gates. |
| Scispark | [`skills/scispark`](skills/scispark/SKILL.md) | Generate evidence-tracked research ideas and testable hypotheses from papers or keywords. |
| Research Baseline Builder | [`skills/research-baseline-builder`](skills/research-baseline-builder/SKILL.md) | Translate a scientific question into data inputs, outputs, baselines, and metrics. |
| Scientific Humanization | [`skills/scientific-humanization`](skills/scientific-humanization/SKILL.md) | Rewrite Chinese scientific text so it sounds natural while preserving facts and evidence boundaries. |
| Scientific Image Generation | [`skills/giiisp-scientific-image-generation`](skills/giiisp-scientific-image-generation/SKILL.md) | Turn paper paragraphs, mechanisms, and experiment flows into scientific image briefs and runs. |
| Visual Deck Builder | [`skills/visual-deck-builder`](skills/visual-deck-builder/SKILL.md) | Build image-model-driven PPT decks from topics, papers, reports, notes, or style references. |
| Manim Agent | [`skills/manim-agent`](skills/manim-agent/SKILL.md) | Create, review, and package mathematical or technical explainer videos. |
| PaperCheck | [`skills/papercheck`](skills/papercheck/SKILL.md) | Audit citations, references, formats, and context support in academic papers. |
| Cognitive Profile | [`skills/cognitive-profile`](skills/cognitive-profile/SKILL.md) | Maintain a reviewable research/user preference profile for long-term collaboration. |
| World Threads Entry | [`skills/world-threads-entry`](skills/world-threads-entry/SKILL.md) | Connect TopicLab / 他山世界 / OpenClaw world-thread workflows. |

See [`docs/skill-package-overview.md`](docs/skill-package-overview.md) for the Chinese package overview.

## Authors and Support

**Authors and contributors**

- Qiao Han (乔晗)
- Zhu Xiaomo (朱晓墨)
- Yu-Yang Li
- Cai Anping (蔡安平)
- Wang Rui (王瑞)
- Fang Zerui (房泽锐)
- OpenAI Codex-assisted development contributors

**Supporting project**

- Panshi AI4Science Ecosystem and Application Model Research Project

## Repository Layout

```text
.
├── assets/                  # Public images used by docs
├── docs/                    # Human-readable package docs
├── skills/                  # Skill directories, each with a SKILL.md entrypoint
├── .github/                 # Issue and PR templates
├── CONTRIBUTING.md          # Collaboration rules
├── SECURITY.md              # Secret and vulnerability policy
├── LICENSE                  # MIT License
├── README.md                # English README
└── README.zh-CN.md          # Chinese README
```

## How to Use a Skill

Each skill is self-contained. Start from its `SKILL.md`, then follow any referenced `scripts/`, `references/`, `templates/`, or `assets/` files in that same skill folder.

For local exploration:

```powershell
git clone https://github.com/Yu-Yang-Li/tashan-research-skills.git
cd tashan-research-skills
Get-ChildItem .\skills -Recurse -Filter SKILL.md
```

To install one skill into a local Codex skill folder on Windows:

```powershell
Copy-Item -Recurse .\skills\papercheck "$env:USERPROFILE\.codex\skills\papercheck"
```

Replace `papercheck` with the skill folder you want to install.

## Engineering Standards

This repository should stay easy to review and hard to turn into unmaintainable code:

- Keep each skill focused on one research job.
- Keep reusable scripts inside the owning skill's `scripts/` directory.
- Prefer Markdown references and structured manifests over large binary-only documentation.
- Do not commit generated run outputs, raw model logs, private papers, credentials, or local caches.
- For changes to scripts, include a smoke test or a documented manual verification command.
- For changes to skill behavior, update the related `SKILL.md` and any referenced docs in the same PR.

## Secret Policy

Do not put API keys, access tokens, bind keys, cookies, private SSH keys, or service credentials in this repository.

Skills that need external services must read secrets from environment variables or local user configuration. Examples include `GIIISP_AUTH_TOKEN`, `DASHSCOPE_API_KEY`, `ALIYUN_DASHSCOPE_API_KEY`, `ARK_API_KEY`, `VOLCENGINE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, and `MINERU_API_TOKEN`.

## License

This project is released under the [MIT License](LICENSE).
