<div align="center">

# 他山科研技能库

**面向科研场景的中英双语 agent 技能库**

*文献证据 · 研究构思 · 成果表达 · 协作沉淀 · 工具测评*

[简体中文](README.md) · [English](README.en.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/Skills-19-2E74B5.svg)](skills/README.md)
[![Modules](https://img.shields.io/badge/%E6%A8%A1%E5%9D%97-5-0B2545.svg)](#技能矩阵)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

<img src="assets/research-skills-overview.png" alt="他山科研技能库概览" width="720" />

</div>

---

## 项目概览

仓库里是我们自己开发的 19 个科研 agent skills，按文献证据、研究构思、成果表达、协作沉淀、工具测评五类整理。每个技能是一个独立文件夹，入口是 `SKILL.md`，配套的脚本、模板和测试放在同一目录，复制进 agent 的 skills 目录就能用。

项目由 **磐石 AI4Science 生态与应用模式研究项目** 支持。

## 科研 Skill / MCP 发现

[`find-science-skills`](skills/find-science-skills/SKILL.md) 用于从科研目录中查找适合当前任务的 Skill 或 MCP。宿主模型先判断“资源类型 × 研究领域 × 研究阶段 × 功能分工”，再调用仅依赖 Python 标准库的确定性筛选器缩小范围；不需要后端服务或 API 密钥。

未指定资源类型时默认搜索 Skill；明确要求 MCP 时搜索 MCP，明确要求两者时使用 `--resource all` 同时搜索并保留资源类型。

当前静态目录包含 1,391 个 Skill 和 5,643 个活动科研 MCP，共用 9 个一级领域、42 个二级领域、5 个研究阶段和 17 个功能组。领域和阶段限定检索边界，功能可作为排序偏好或严格过滤条件。脚本返回的是待语义复核候选，不把目录顺序冒充相关性结论；宿主模型最终只推荐研究对象和预期产物都直接匹配的资源，找不到时明确报告目录缺口。

```powershell
# 查看合法分类
python .\skills\find-science-skills\scripts\filter_science_resources.py --list-dimensions

# 查看指定领域和阶段下实际存在的功能组
python .\skills\find-science-skills\scripts\filter_science_resources.py `
  --domain 生命科学 --stage 分析验证 --list-functions

# 同时搜索 Skill 和 MCP
python .\skills\find-science-skills\scripts\filter_science_resources.py `
  --resource all --domain 生命科学 --stage 分析验证 `
  --function 数据处理 --strict-function --json

# 严格筛选并输出机器可读结果
python .\skills\find-science-skills\scripts\filter_science_resources.py `
  --resource mcp `
  --domain 生命科学 --subdomain 生物信息学 --stage 分析验证 `
  --function 数据处理 --strict-function --json
```

完整判断规则、可信状态和回复格式见 [`skills/find-science-skills/SKILL.md`](skills/find-science-skills/SKILL.md)。

## 技能矩阵

### 文献证据

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| Skill / MCP 发现 | [`skills/find-science-skills`](skills/find-science-skills/SKILL.md) | 按研究领域、研究阶段和功能分工筛选 1,391 个科研 Skill 与 5,643 个活动科研 MCP，并保留来源与可信状态供宿主模型复核。 |
| 论文检索 | [`skills/giiisp-paper-search-apis`](skills/giiisp-paper-search-apis/SKILL.md) | 基于 Giiisp 和开放论文数据源，快速查找候选文献，并整理可核验的论文列表。 |
| 深度研究 | [`skills/sci-employee-deep-research`](skills/sci-employee-deep-research/SKILL.md) | 围绕研究问题拆关键词、找证据、梳理引用，并标出结论的证据边界。 |
| 论文审查 | [`skills/thesis-audit-reviewer`](skills/thesis-audit-reviewer/SKILL.md) | 审查论文或学位论文中的事实、方法、引用、证据边界和完成度。 |

### 研究构思

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| 假设生成 | [`skills/scispark`](skills/scispark/SKILL.md) | 基于关键词或论文集合生成带证据追踪的研究想法、假设和机制线索。 |
| 数据处理 | [`skills/research-baseline-builder`](skills/research-baseline-builder/SKILL.md) | 把科研问题拆成可处理的数据任务，明确输入、输出、baseline 和评估指标。 |
| 实验设计 | [`skills/experiment-design`](skills/experiment-design/SKILL.md) | 在采集数据之前完成研究设计：设计类型、随机化、样本量、统计功效和分析计划。 |
| 统计分析 | [`skills/statistical-analysis`](skills/statistical-analysis/SKILL.md) | 数据采集后按分析计划执行验证性统计：检验、效应量、置信区间、前提检查和多重比较校正。 |

### 成果表达

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| 文本润色 | [`skills/scientific-humanization`](skills/scientific-humanization/SKILL.md) | 优化中文论文、基金、答辩和讲稿表达，让文字更自然，同时保留事实边界。 |
| 学术写作 | [`skills/academic-writing`](skills/academic-writing/SKILL.md) | 覆盖论文写作、同行评审、审稿回复、基金申请和投稿材料的“写—审—改—投”全流程。 |
| 科研绘图 | [`skills/giiisp-scientific-image-generation`](skills/giiisp-scientific-image-generation/SKILL.md) | 把论文段落、机制描述或实验流程转成科研图像生成任务。 |
| PPT 制作 | [`skills/visual-deck-builder`](skills/visual-deck-builder/SKILL.md) | 把主题、论文、报告或笔记整理成结构清晰、视觉完整的演示文稿。 |
| 讲解视频 | [`skills/manim-agent`](skills/manim-agent/SKILL.md) | 生成数学、公式或技术概念的讲解动画，可按需要加入配音。 |
| 实操课程 | [`skills/practical-course-producer`](skills/practical-course-producer/SKILL.md) | 把带有真实状态变化和验证步骤的工具工作流制作成可复现的实操课程视频。 |

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

## 作者与支持

**作者与贡献者**

乔晗 · 朱晓墨 · Yu-Yang Li · 蔡安平 · 王瑞 · 房泽锐

**支持项目**

磐石 AI4Science 生态与应用模式研究项目

## 许可证

本项目采用 [MIT License](LICENSE)。
