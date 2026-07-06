---
title: "cfd-mesh-gate"
type: skill
tags: ["建模仿真", "计算工程与流体仿真", "C"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
skill_id: "cfd-mesh-gate"
quality_score: 60
tier: C
needs_review: false
source_repo: "csml-rpi/AI-CFD-Scientist"
source_path: "cfd-skills/cfd-mesh-gate/SKILL.md"
---

# cfd-mesh-gate
## 一句话定位
[来源] Mandatory mesh-independence study before any experiments. Per physics group, run baseline + refined meshes (10% near-wall, 5% away-from-wall), compare QoIs against the 5% threshold, escalate to GCI if needed, lock the selected mesh. Self-contained protocol emb

## 检索线索
- 能力组：建模仿真
- 功能家族：执行实验
- 学科：工程与环境 / 计算工程与流体仿真
- 中文关键词：CFD网格独立性验证, 网格细化策略, 近壁网格加密, 远壁网格加密, 物理量收敛性分析, 品质指标QoI, 网格收敛指数GCI, 计算流体力学建模, 工程仿真, 环境流体模拟

## 质量信号
| 指标 | 值 |
| --- | --- |
| 质量分 | 60 |
| Tier | C |
| 深评 | 未深评 |
| 来源仓库数 | 1 |
| stars | 31 |
| 待复核 | 否 |

## 获取方式
- 仓库：`csml-rpi/AI-CFD-Scientist`
- 路径：`cfd-skills/cfd-mesh-gate/SKILL.md`

## 图关系
- 可替代：[[skills/openfoam-agent]] (0.400)、[[skills/cfd-mesh-independence]] (0.365)、[[skills/slurm-job-script-generator]] (0.347)、[[skills/workflow-engine-mapper]] (0.316)、[[skills/simulation-orchestrator]] (0.316)、[[skills/numerical-integration]] (0.300)、[[skills/nonlinear-solvers]] (0.300)、[[skills/mesh-generation]] (0.300)
- 配套：[[skills/cfd-paper-writer]]、[[skills/cfd-code-mod]]、[[skills/cfd-viz]]、[[skills/cfd-experiment]]、[[skills/cfd-mesh-independence]]、[[skills/cfd-research]]、[[skills/cfd-pipeline]]、[[skills/cfd-paper]]
- 下一步：[[skills/medical-study-design-gatekeeper|medical_study_design_gatekeeper]] (0.123)
- 相关：[[skills/md-analysis-planner]] (0.300)、[[skills/time-stepping]] (0.300)、[[skills/performance-profiling]] (0.300)、[[skills/differentiation-schemes]] (0.300)、[[skills/simulation-failure-triage]] (0.300)、[[skills/fair-simulation-packager]] (0.300)、[[skills/linear-solvers]] (0.300)、[[skills/numerical-stability]] (0.300)

## 反向链接
- [[skills/cfd-cross-analyze]]（配套）
- [[skills/cfd-open-discovery]]（可替代 (0.236)）
- [[skills/cfd-open-discovery]]（配套）
- [[skills/cfd-experiment]]（配套）
- [[skills/experiment-plan]]（下一步 (0.133)）
- [[skills/cfd-code-modify]]（配套）
- [[skills/cfd-code-modify]]（相关 (0.271)）
- [[skills/cfd-hypothesis]]（配套）
- [[skills/cfd-pipeline]]（配套）
- [[skills/cfd-requirements]]（配套）
- [[skills/cfd-requirements]]（相关 (0.292)）
- [[skills/cfd-code-mod]]（配套）
