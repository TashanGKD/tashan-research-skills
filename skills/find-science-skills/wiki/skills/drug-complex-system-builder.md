---
title: "drug-complex-system-builder"
type: skill
tags: ["建模仿真", "药物发现", "C"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
skill_id: "drug-complex-system-builder"
quality_score: 64
tier: C
needs_review: false
source_repo: "learningmatter-mit/AtomisticSkills"
source_path: ".agents/skills/drug-complex-system-builder/SKILL.md"
---

# drug-complex-system-builder
## 一句话定位
[来源] Build a solvated, charge-neutralized protein-ligand complex for OpenMM molecular dynamics simulation. Combines a prepared receptor PDB and ligand SDF, parameterizes the ligand with OpenFF Sage or GAFF (AM1-BCC charges), applies Amber ff14SB to the protein, solvates with explicit water, and adds coun

## 检索线索
- 能力组：建模仿真
- 功能家族：执行实验
- 学科：化学与药物 / 药物发现
- 中文关键词：分子动力学模拟系统构建, OpenMM, 蛋白-配体复合物, PDB, SDF, OpenFF Sage, GAFF, AM1-BCC, ff14SB, 显式水溶剂化, 反离子添加, 模拟盒子构建

## 质量信号
| 指标 | 值 |
| --- | --- |
| 质量分 | 64 |
| Tier | C |
| 深评 | 未深评 |
| 来源仓库数 | 1 |
| stars | 126 |
| 待复核 | 否 |

## 获取方式
- 仓库：`learningmatter-mit/AtomisticSkills`
- 路径：`.agents/skills/drug-complex-system-builder/SKILL.md`

## 图关系
- 可替代：[[skills/drug-mmpbsa-gbsa]] (0.284)、[[skills/openfold3]] (0.248)、[[skills/chai1]] (0.240)、[[skills/drug-protein-ligand-md]] (0.238)、[[skills/drug-binding-site-definition]] (0.229)、[[skills/antechamber]] (0.228)、[[skills/diffdock]] (0.198)、[[skills/drug-ligand-prep]] (0.194)
- 配套：[[skills/chem-dft-orca-advanced-calculation]]、[[skills/chem-nmr-analysis]]、[[skills/chem-spectrum-matcher]]、[[skills/chem-db-qmof]]、[[skills/drug-protein-ligand-md]]、[[skills/chem-solution-md]]、[[skills/chem-dft-orca-singlepoint]]、[[skills/drug-binding-site-definition]]
- 下一步：[[skills/tooluniverse-drug-repurposing]] (0.129)
- 相关：[[skills/medicare-drug-stats]] (0.239)、[[skills/drug-interaction-checker]] (0.220)、[[skills/agentd-drug-discovery]] (0.206)、[[skills/pediatric-drug-dosing]] (0.201)、[[skills/boltz]] (0.191)、[[skills/drug-pose-validation]] (0.191)、[[skills/oer-overpotential]] (0.191)、[[skills/drug-admet-prediction]] (0.185)

## 反向链接
- [[skills/drug-admet-prediction]]（可替代 (0.185)）
- [[skills/drug-binding-site-definition]]（可替代 (0.229)）
- [[skills/drug-mmpbsa-gbsa]]（可替代 (0.284)）
- [[skills/drug-pose-validation]]（可替代 (0.191)）
- [[skills/pediatric-drug-dosing]]（相关 (0.201)）
- [[skills/cross-disease-shared-biomarker-network-research-planner]]（相关 (0.181)）
- [[skills/figma-generate-library]]（相关 (0.167)）
