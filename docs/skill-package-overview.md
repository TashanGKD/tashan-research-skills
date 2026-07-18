# 科研助理技能包

本技能包面向科研场景，支持用户完成文献查证、研究设计、材料撰写、成果呈现与协作沉淀等常见任务，帮助把分散的科研工作整理成更顺畅、可复用的工作流程。

## 能力总览

| 模块 | 核心能力 | 输出价值 |
| --- | --- | --- |
| 文献证据 | 基于文献库和开放论文数据源，快速查找候选文献；结合深度研究能力拆解关键词、召回证据、梳理引用，并标出结论的证据边界。 | 帮助用户从海量论文中快速定位可核验的研究线索，避免停留在泛泛搜索结果，提升选题、综述、调研和论文依据整理的质量。 |
| 研究构思 | 基于关键词、论文集合或初步问题生成研究假设、机制线索和初步方案；把科研问题拆成可处理的数据任务，明确输入、输出、baseline 和评估指标；在采集数据之前完成实验设计、随机化、样本量和分析计划。 | 把“我想研究什么”进一步转化为可执行的研究路线，帮助用户更快形成假设、实验思路、数据方案和统计上站得住的研究设计。 |
| 成果表达 | 支持论文、基金、答辩和讲稿润色；覆盖论文写作、同行评审、审稿回复、基金申请和投稿材料；可把研究主题、机制原理、实验流程、论文段落转成科研图像、PPT 和讲解视频。 | 让科研成果不只停留在文字草稿中，而是进一步变成结构清晰、视觉完整、便于汇报、答辩、投稿和传播的材料。 |
| 协作沉淀 | 检查论文引文、参考文献、格式和上下文支撑关系；记录研究偏好、表达习惯和协作边界；把日常科研对话沉淀为长期分身记忆；接入他山世界获取前沿信息、科研社交和更多科研技能发现。 | 减少引用错配和证据断裂，让长期科研辅助逐渐理解用户的研究方向、表达习惯和协作需求，把一次性任务沉淀成持续可复用的科研工作流。 |
| 工具测评 | 部署并测试 MCP 服务的协议连通、工具行为和仓库健康度；评估 Agent Skill 的规范合规、安全性、实际提升和触发质量。 | 在把外部工具和技能纳入科研工作流之前先做把关，减少装了不能用、用了不可靠的返工成本。 |

## 包含技能

### 文献证据

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| 论文检索 | [`skills/giiisp-paper-search-apis`](../skills/giiisp-paper-search-apis/SKILL.md) | 基于 Giiisp 和开放论文数据源，快速查找候选文献，并整理可核验的论文列表。 |
| 深度研究 | [`skills/sci-employee-deep-research`](../skills/sci-employee-deep-research/SKILL.md) | 围绕研究问题拆关键词、找证据、梳理引用，并标出结论的证据边界。 |
| 论文审查 | [`skills/thesis-audit-reviewer`](../skills/thesis-audit-reviewer/SKILL.md) | 审查论文或学位论文中的事实、方法、引用、证据边界和完成度。 |

### 研究构思

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| 假设生成 | [`skills/scispark`](../skills/scispark/SKILL.md) | 基于关键词或论文集合生成研究假设、机制线索和初步方案。 |
| 数据处理 | [`skills/research-baseline-builder`](../skills/research-baseline-builder/SKILL.md) | 把科研问题拆成可处理的数据任务，明确输入、输出和评估指标。 |
| 实验设计 | [`skills/experiment-design`](../skills/experiment-design/SKILL.md) | 在采集数据之前完成研究设计：设计类型、随机化、样本量、统计功效和分析计划。 |
| 统计分析 | [`skills/statistical-analysis`](../skills/statistical-analysis/SKILL.md) | 数据采集后按分析计划执行验证性统计：检验、效应量、置信区间、前提检查和多重比较校正。 |

### 成果表达

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| 文本润色 | [`skills/scientific-humanization`](../skills/scientific-humanization/SKILL.md) | 优化论文、基金、答辩和讲稿表达，保留事实边界。 |
| 学术写作 | [`skills/academic-writing`](../skills/academic-writing/SKILL.md) | 覆盖论文写作、同行评审、审稿回复、基金申请和投稿材料的“写—审—改—投”全流程。 |
| 科研绘图 | [`skills/giiisp-scientific-image-generation`](../skills/giiisp-scientific-image-generation/SKILL.md) | 把论文段落、机制描述或实验流程转成科研图像生成任务。 |
| PPT 制作 | [`skills/visual-deck-builder`](../skills/visual-deck-builder/SKILL.md) | 把主题、论文或报告整理成结构清晰、视觉完整的演示文稿。 |
| 讲解视频 | [`skills/manim-agent`](../skills/manim-agent/SKILL.md) | 生成数学、公式或技术概念的讲解动画，可按需要加入配音。 |
| 实操课程 | [`skills/practical-course-producer`](../skills/practical-course-producer/SKILL.md) | 把具有真实起始状态、工具操作、状态变化和验证步骤的工作流制作成可复现的课程视频。 |

### 协作沉淀

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| 引用合规 | [`skills/papercheck`](../skills/papercheck/SKILL.md) | 检查论文引文、参考文献、格式和上下文支撑关系。 |
| 科研画像 | [`skills/cognitive-profile`](../skills/cognitive-profile/SKILL.md) | 记录研究偏好、表达习惯和协作边界，内置“做梦”式深度整理，逐步形成科研数字分身（配套 Dream 巩固层 [`skills/research-dream`](../skills/research-dream/SKILL.md) 可选安装，不单独上架）。 |
| 他山世界 | [`skills/world-threads-entry`](../skills/world-threads-entry/SKILL.md) | 支持前沿信息获取、科研社交和更多科研技能发现。 |

### 工具测评

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| MCP 测评 | [`skills/mcp-criticagent`](../skills/mcp-criticagent/SKILL.md) | 部署、测试并评分 MCP 服务与工具：协议连通、行为测试和仓库健康度。 |
| 技能测评 | [`skills/skill-criticagent`](../skills/skill-criticagent/SKILL.md) | 在安装 Agent Skill 之前评估规范合规、安全性、实际提升和触发质量。 |

## 使用定位

| 定位 | 说明 |
| --- | --- |
| 证据先行 | 适合用于选题、综述、调研和论文依据整理，先明确结论能被哪些文献支撑。 |
| 方案落地 | 适合把模糊研究问题拆成可执行的数据任务、实验思路、baseline 和评估指标。 |
| 表达成品 | 适合把论文段落、机制原理、实验流程和研究主题转成文字、图像、PPT 或讲解视频。 |
| 长期协作 | 适合沉淀引用规范、个人表达习惯、研究偏好和可复用的科研工作流。 |
