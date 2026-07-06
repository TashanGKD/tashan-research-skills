<div align="center">

# 他山科研技能库

**面向科研场景的中英双语 agent 技能库**

*文献证据 · 研究构思 · 成果表达 · 协作沉淀 · 工具测评*

[简体中文](README.md) · [English](README.en.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/Skills-16-2E74B5.svg)](skills/README.md)
[![Modules](https://img.shields.io/badge/%E6%A8%A1%E5%9D%97-5-0B2545.svg)](#技能矩阵)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

<img src="assets/research-skills-overview.png" alt="他山科研技能库概览" width="720" />

</div>

---

## 项目概览

他山科研技能库收录 **16 个 agent skills**，对应科研工作里反复出现的任务：查文献、核证据，把想法变成可检验的研究设计，把成果做成论文、图像、PPT 和讲解视频，以及长期协作中的偏好记忆。每个 skill 是一个独立目录，`SKILL.md` 是入口，脚本、参考文档、模板和测试都在同一个目录里。

本项目由 **磐石 AI4Science 生态与应用模式研究项目** 支持。

### 设计原则

几条贯穿整个库的做法：

- 一个技能只管一件事。检索不掺和写作，写作不掺和引用核验，边界写在各自的 `SKILL.md` 里，装哪个用哪个。
- 结论跟着证据走。检索、审查、调研类技能都要求给出处，证据不够的地方直接标“待核验”，不替用户把话说满。
- 能写成脚本的不交给模型。解析、随机化、打包、校验都是带测试的普通脚本，改坏了测试先报警；模型只处理需要判断的部分。
- 密钥不进仓库。凭证一律在运行时从环境变量读，文档里只出现变量名和申请地址。

## 技能矩阵

### 文献证据

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| 论文检索 | [`skills/giiisp-paper-search-apis`](skills/giiisp-paper-search-apis/SKILL.md) | 基于 Giiisp 和开放论文数据源，快速查找候选文献，并整理可核验的论文列表。 |
| 深度研究 | [`skills/sci-employee-deep-research`](skills/sci-employee-deep-research/SKILL.md) | 围绕研究问题拆关键词、找证据、梳理引用，并标出结论的证据边界。 |
| 论文审查 | [`skills/thesis-audit-reviewer`](skills/thesis-audit-reviewer/SKILL.md) | 审查论文或学位论文中的事实、方法、引用、证据边界和完成度。 |

### 研究构思

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| 假设生成 | [`skills/scispark`](skills/scispark/SKILL.md) | 基于关键词或论文集合生成带证据追踪的研究想法、假设和机制线索。 |
| 数据处理 | [`skills/research-baseline-builder`](skills/research-baseline-builder/SKILL.md) | 把科研问题拆成可处理的数据任务，明确输入、输出、baseline 和评估指标。 |
| 实验设计 | [`skills/experiment-design`](skills/experiment-design/SKILL.md) | 在采集数据之前完成研究设计：设计类型、随机化、样本量、统计功效和分析计划。 |

### 成果表达

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| 文本润色 | [`skills/scientific-humanization`](skills/scientific-humanization/SKILL.md) | 优化中文论文、基金、答辩和讲稿表达，让文字更自然，同时保留事实边界。 |
| 学术写作 | [`skills/academic-writing`](skills/academic-writing/SKILL.md) | 覆盖论文写作、同行评审、审稿回复、基金申请和投稿材料的“写—审—改—投”全流程。 |
| 科研绘图 | [`skills/giiisp-scientific-image-generation`](skills/giiisp-scientific-image-generation/SKILL.md) | 把论文段落、机制描述或实验流程转成科研图像生成任务。 |
| PPT 制作 | [`skills/visual-deck-builder`](skills/visual-deck-builder/SKILL.md) | 把主题、论文、报告或笔记整理成结构清晰、视觉完整的演示文稿。 |
| 讲解视频 | [`skills/manim-agent`](skills/manim-agent/SKILL.md) | 生成数学、公式或技术概念的讲解动画，可按需要加入配音。 |

### 协作沉淀

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| 引用合规 | [`skills/papercheck`](skills/papercheck/SKILL.md) | 检查论文引文、参考文献、格式和上下文支撑关系。 |
| 科研画像 | [`skills/cognitive-profile`](skills/cognitive-profile/SKILL.md) | 记录研究偏好、表达习惯和协作边界，内置“做梦”式深度整理，让长期辅助逐步形成科研数字分身。配套 Dream 巩固层见 [`skills/research-dream`](skills/research-dream/SKILL.md)（可选安装，不单独上架）。 |
| 他山世界 | [`skills/world-threads-entry`](skills/world-threads-entry/SKILL.md) | 接入 TopicLab / 他山世界 / OpenClaw，支持前沿信息获取和科研协作。 |

### 工具测评

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| MCP 测评 | [`skills/mcp-criticagent`](skills/mcp-criticagent/SKILL.md) | 部署、测试并评分 MCP 服务与工具：协议连通、行为测试和仓库健康度。 |
| 技能测评 | [`skills/skill-criticagent`](skills/skill-criticagent/SKILL.md) | 在安装 Agent Skill 之前评估规范合规、安全性、实际提升和触发质量。 |

更多中文能力说明见 [`docs/skill-package-overview.md`](docs/skill-package-overview.md)，机读索引见 [`skills/README.md`](skills/README.md)。

## 快速上手

每个 skill 都是自包含目录：先阅读对应目录下的 `SKILL.md`，再按其中引用的 `scripts/`、`references/`、`templates/` 或 `assets/` 执行。

**1. 克隆仓库**

```powershell
git clone https://github.com/TashanGKD/tashan-research-skills.git
cd tashan-research-skills
Get-ChildItem .\skills -Recurse -Filter SKILL.md
```

**2. 把技能安装到你的 agent 运行环境**

```powershell
# Codex（Windows）
Copy-Item -Recurse .\skills\papercheck "$env:USERPROFILE\.codex\skills\papercheck"

# Claude Code / Cursor 等兼容 SKILL.md 的运行环境：
# 把技能文件夹复制到对应的 skills 目录即可。
```

把 `papercheck` 换成需要安装的 skill 目录名。技能之间没有相互依赖，可以只装需要的子集。

**3. 配置凭证（仅在技能需要时）**

技能在运行时从环境变量读取密钥。没配 key 也能用：有的转 dry-run，有的走本地回退，实在跑不了会把卡在哪一步写清楚，不会伪造结果。

| 环境变量 | 使用技能 | 用途 | 申请地址 |
| --- | --- | --- | --- |
| `GIIISP_AUTH_TOKEN` | 科研绘图、PPT 制作、论文检索 | Giiisp API 访问（图像生成、检索） | [giiisp.com](https://giiisp.com/#/mcp/authenticate) |
| `DASHSCOPE_API_KEY` | 讲解视频、科研绘图、PPT 制作、MCP 测评 | 场景生成、Qwen 视觉审查、CosyVoice 配音、行为测试 | [阿里云百炼](https://help.aliyun.com/zh/model-studio/get-api-key) |
| `MINERU_API_TOKEN` | 论文审查 | 可选的 MinerU 在线 PDF 解析（有本地回退） | [mineru.net](https://mineru.net/apiManage/token) |

讲解视频（Manim Agent）走阿里云百炼的 Claude Code 兼容路线，场景生成与 CosyVoice 配音复用同一个 `DASHSCOPE_API_KEY`，不需要单独申请 Anthropic key。

## 仓库结构

```text
.
├── assets/                  # README 和文档使用的公开图片
├── docs/                    # 面向用户阅读的技能包说明（中文总览）
├── skills/                  # 技能目录，每个以 SKILL.md 为入口
├── .github/                 # issue 和 PR 模板
├── manifest.yml             # 机读技能索引（id / 分类 / 入口）
├── CONTRIBUTING.md          # 协作规则
├── SECURITY.md              # 密钥和安全策略
├── LICENSE                  # MIT License
├── README.md                # 中文 README（默认）
└── README.en.md             # 英文 README
```

## 工程标准

给改仓库的人几条约定，目的是让 PR 好审，半年后还能维护：

- 新技能先想清楚它负责哪一件科研任务；一个目录说不清楚的，拆成两个。
- 脚本放进所属技能的 `scripts/`，不建全局工具目录。
- 关键信息写在 Markdown 里；图片、模板这类二进制文件可以有，但不能是唯一的信息来源。
- 运行产物、模型日志、别人的论文、密钥、本地缓存，都不进版本库。
- 改了脚本，PR 里给一条能跑的验证命令，或者补 smoke test。
- 改了技能行为，`SKILL.md` 和它引用的文档在同一个 PR 里一起改。

## 安全策略

API key、access token、bind key、cookie、SSH 私钥，不允许出现在仓库任何位置，示例和测试也不例外。需要外部服务的技能，在运行时从环境变量读凭证。发现泄漏或可利用的脚本问题，按 [`SECURITY.md`](SECURITY.md) 的方式私下报告，不要开公开 issue。

## 参与贡献

新技能、修 bug、补测试、改文档都欢迎。动手前看一眼 [`CONTRIBUTING.md`](CONTRIBUTING.md)，要求就三条：一个 PR 只动一个技能的范围；改脚本要附验证方式；改行为要同步改 `SKILL.md`。

## 作者与支持

**作者与贡献者**

乔晗 · 朱晓墨 · Yu-Yang Li · 蔡安平 · 王瑞 · 房泽锐

**支持项目**

磐石 AI4Science 生态与应用模式研究项目

## 许可证

本项目采用 [MIT License](LICENSE)。
