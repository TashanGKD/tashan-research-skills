---
title: "cfd-orchestrator"
type: skill
tags: ["建模仿真", "计算工程与流体仿真", "C"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
skill_id: "cfd-orchestrator"
quality_score: 56
tier: C
needs_review: false
source_repo: "csml-rpi/AI-CFD-Scientist"
source_path: "skills/cfd-orchestrator/SKILL.md"
---

# cfd-orchestrator
## 一句话定位
[来源] Top-level CFD scientist orchestrator. Reads a user CFD topic, picks one route, initializes a run directory, and invokes the first skill of a fixed chain. From that point on, every per-stage skill's `## Next` block names the next skill, and the agent walks the

## 检索线索
- 能力组：建模仿真
- 功能家族：执行实验
- 学科：工程与环境 / 计算工程与流体仿真
- 中文关键词：CFD建模, 流体仿真, 计算流体力学, CFD-orchestrator, 仿真流程编排, CFD工作流调度, 工程仿真, 环境流体模拟

## 质量信号
| 指标 | 值 |
| --- | --- |
| 质量分 | 56 |
| Tier | C |
| 深评 | 未深评 |
| 来源仓库数 | 1 |
| stars | 31 |
| 待复核 | 否 |

## 获取方式
- 仓库：`csml-rpi/AI-CFD-Scientist`
- 路径：`skills/cfd-orchestrator/SKILL.md`

## 图关系
- 可替代：[[skills/openfoam-agent]] (0.436)、[[skills/cfd-research]] (0.401)、[[skills/cfd-pipeline]] (0.349)、[[skills/cfd-hypothesis]] (0.314)、[[skills/cfd-paper]] (0.295)、[[skills/openfoam-sim]] (0.293)、[[skills/slurm-job-script-generator]] (0.293)、[[skills/cfd-mesh-independence]] (0.288)
- 配套：[[skills/cfd-paper-writer]]、[[skills/cfd-mesh-gate]]、[[skills/cfd-code-mod]]、[[skills/cfd-viz]]、[[skills/cfd-experiment]]、[[skills/cfd-mesh-independence]]、[[skills/cfd-research]]、[[skills/cfd-pipeline]]
- 下一步：[[skills/paper-memory-builder]] (0.130)
- 相关：[[skills/hpc-su2]] (0.278)、[[skills/simulation-orchestrator]] (0.272)、[[skills/workflow-engine-mapper]] (0.272)、[[skills/cfd-experiment]] (0.266)、[[skills/defect-generation]] (0.266)、[[skills/cfd-foamagent]] (0.252)、[[skills/nrr-overpotential]] (0.252)、[[skills/convergence-study]] (0.250)

## 反向链接
- [[skills/island-select]]（下一步 (0.139)）
- [[skills/co-scientist-pipeline]]（下一步 (0.144)）
- [[skills/research-overview-pipeline]]（下一步 (0.143)）
- [[skills/agent-memory-systems]]（相关 (0.182)）
- [[skills/meta-apply]]（可替代 (0.229)）
- [[skills/brainblast-fleet]]（相关 (0.150)）
- [[skills/cfd-hypothesis]]（相关 (0.314)）
- [[skills/cfd-pipeline]]（可替代 (0.349)）
- [[skills/cfd-research]]（可替代 (0.401)）
- [[skills/cfd-literature]]（可替代 (0.197)）
- [[skills/paper-orchestrator]]（相关 (0.212)）
- [[skills/cfd-paper]]（可替代 (0.295)）
