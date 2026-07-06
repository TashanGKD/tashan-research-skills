---
name: find-science-skills
description: 发现并推荐科研/学术/实验/仿真类 agent skill 的科研版 find-skills。当用户问"怎么做 X 科研任务""有没有做 X 的 skill""帮我找一个文献/仿真/实验/数据分析的技能"，或想扩展科研能力、想知道某方向该装哪个 skill 时使用。基于他山托管的科研技能图谱检索（技能↔技能关系 + CriticAgent 质量分 + 深度评测），每次用前可 git 拉取最新版本。数据源是本项目自建、清洗去重后的科研 registry，而非通用 skill 市场。
---

# Find Science Skills（科研版 find-skills）

对标 `vercel-labs/skills` 的 `npx skills find`，但数据源是他山自建、清洗去重后的**科研技能图谱**
（约 1400 个 canonical 科研技能，5 功能家族 / 12 功能组）。相比纯关键词检索，它带两层优化：

1. **证据排序**：命中度 + CriticAgent 质量分 + 深度评测结论 + 多仓库共识 + stars，不只看关键词。
2. **图感知推荐（skill graph）**：每个命中带出它的图邻居——同类可替代 / 同仓库配套 / 工作流下一步，
   帮 agent 组出一条连贯的技能序列，而不是给一堆孤立结果。

技能图谱数据托管在本仓库 `github.com/TashanGKD/tashan-research-skills`，随仓库持续更新；
每次使用前用 `--update` 先 `git pull`，即可拿到最新的技能库再检索。

## 何时使用

- 用户问"怎么做 X"（X = 常见科研任务：查文献、跑 DFT、单细胞分析、分子对接、写论文…）
- 用户说"有没有做 X 的 skill / 帮我找个 X 技能"
- 用户想按能力簇浏览（12 功能组：论文检索 / 综述阅读 / 数据库检索 / 智能体编排 / 建模仿真 /
  仪器实验 / 数据处理 / 统计分析 / 论文写作 / 引用管理 / 投稿评审 / 可视化展示）
- 用户想知道某方向该装什么、或某个技能有哪些配套/替代

## 工作流（先更新，再检索）

### 0. 确保技能库最新
本 skill 的数据（`data/skill_graph_index.json`）随本仓库分发。第一次用前若还没拉取仓库：

```bash
git clone https://github.com/TashanGKD/tashan-research-skills
cd tashan-research-skills/skills/find-science-skills
```

之后每次检索加 `--update`，脚本会先对本仓库 `git pull --ff-only` 再检索（拉不动时自动回退到本地数据）：

```bash
python scripts/find_skills.py --update "single cell rna"
```

### 1. 理解需求
识别科研领域（材料/生信/CFD…）、具体任务（查文献/跑仿真/做图…）、大概落在哪个功能组。

### 2. 先看能力簇 leaderboard
`--list-capabilities` 列出 12 功能组及各组高分代表。头部（统计分析、建模仿真、智能体编排）供给足；
尾部（仪器实验）稀缺，命中率低时提醒用户。

### 3. 检索
用具体关键词而非泛词："single cell rna" 优于 "bio"；"DFT" 优于 "计算"。命不中时换同义词或加 `-c` 能力过滤。

### 4. 荐前核证据（不要只看排名）
- **质量分**：CriticAgent 综合分（合规+证据+置信+卫生+深评），≥70 绿、50-70 黄、<50 红。
- **深评结论**：带 `[深评:建议安装]` 是端到端跑过"带/不带对比+触发测试"的最强信号；`[深评:先修复]` 要警示。
- **repo_count**：多个仓库都提供 → 更成熟通用。
- **stars**：来源仓库星数，可信度参考；只是发现信号，不等于真实使用量。
- **[待复核]**：分类置信低，推荐时说明"分类可能不准"。

### 5. 用图邻居组方案（skill graph 的价值）
命中一个技能后，用 `--graph` 或 `--show <id>` 看它的：
- **可替代**：同功能组的替代品，给用户备选。
- **同仓库配套**：常一起用的技能，一并推荐。
- **工作流下一步**：研究流程里的下一环（发现→构想→执行→分析→发表），把整条链串起来。

### 6. 呈现给用户
给出：技能名 + 功能组/学科、来源仓库 + stars + 质量分、示例 `SKILL.md` 路径、获取方式，
并按需附上"可搭配 / 可替代 / 下一步"。

## 命令速查

```bash
python scripts/find_skills.py "single cell rna"            # 关键词检索（证据排序）
python scripts/find_skills.py --update "molecular docking" # 先更新数据再检索
python scripts/find_skills.py "DFT 第一性原理" -n 5 --graph # 展开图邻居
python scripts/find_skills.py --capability 建模仿真 -n 10   # 按能力簇过滤（中英别名）
python scripts/find_skills.py --owner Hello-QM "vasp"      # 按 owner 过滤
python scripts/find_skills.py --list-capabilities          # 能力簇 leaderboard
python scripts/find_skills.py --show diffdock              # 查看单技能及其图邻居
python scripts/find_skills.py "cryo em" --json             # 机器可读（含邻居 id）
```

示例回复：

```
找到适合的科研 skill：
「diffdock」——分子对接（建模仿真 / 药物发现），来自 K-Dense-AI/scientific-agent-skills（30.2k★，3 仓库，质量分 66）。
路径：skills/diffdock/SKILL.md
可替代：autodock-vina-docking；下一步可接可视化/写作类技能。
获取：git clone https://github.com/K-Dense-AI/scientific-agent-skills 后取该路径。
```

### 没找到时
1. 说明科研 registry 里没有现成的；
2. 用通用能力直接帮用户完成任务；
3. 若是高频科研需求，指向"可转化科研工具"（从对应工具 README 起草新 `SKILL.md`）。

## 数据与更新

- `data/skill_graph_index.json`：技能图谱（节点=技能、边=技能↔技能关系，含质量分/深评）。
- `data/data_version.json`：数据版本（技能数 / 边数 / 生成时间）。
- 数据由 TopicLab 科研技能发现流水线定期重建并推送进本仓库；用户侧只需 `git pull`（或 `--update`）即可拿到最新版本。
- 脚本仅依赖 Python 标准库，无需安装额外包即可检索。

## 与通用 skill 市场的关系

通用/前端/DevOps 需求转向 `vercel-labs/skills`（`npx skills find`）或 `skills.sh`。
本 skill 只覆盖**科研/学术/实验/仿真**方向，数据来自 GitHub 上真实的科研 `SKILL.md` 仓库并经清洗去重与质量评测。
