---
title: "drug-pocket-detection"
type: skill
tags: ["建模仿真", "计算机视觉", "C"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
skill_id: "drug-pocket-detection"
quality_score: 64
tier: C
needs_review: false
source_repo: "learningmatter-mit/AtomisticSkills"
source_path: ".agents/skills/drug-pocket-detection/SKILL.md"
---

# drug-pocket-detection
## 一句话定位
[来源] Identify and rank ligandable pockets on a protein structure or model using geometry (fpocket) or an ML predictor (P2Rank). Returns ranked pockets with lining residues, geometric center, volume, and a druggability score per pocket. Excludes docking; pair with drug-binding-site-definition or drug-dock

## 检索线索
- 能力组：建模仿真
- 功能家族：执行实验
- 学科：AI与计算机 / 计算机视觉
- 中文关键词：药物口袋检测, fpocket, P2Rank, 蛋白质结合位点预测, 配体结合口袋识别, 口袋可药性评分, 蛋白质结构建模, 几何中心定位, 口袋体积计算, lining residues分析, AI蛋白质建模, 计算机辅助药物设计

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
- 路径：`.agents/skills/drug-pocket-detection/SKILL.md`

## 图关系
- 可替代：[[skills/drug-binding-site-definition]] (0.301)、[[skills/ligandmpnn]] (0.208)、[[skills/boltz]] (0.201)、[[skills/cfd-interpret]] (0.199)、[[skills/chai1]] (0.193)、[[skills/drug-docking-vina]] (0.190)、[[skills/openfold3]] (0.177)、[[skills/nrr-overpotential]] (0.173)
- 配套：[[skills/chem-dft-orca-advanced-calculation]]、[[skills/chem-nmr-analysis]]、[[skills/chem-spectrum-matcher]]、[[skills/chem-db-qmof]]、[[skills/drug-protein-ligand-md]]、[[skills/chem-solution-md]]、[[skills/chem-dft-orca-singlepoint]]、[[skills/drug-binding-site-definition]]
- 相关：[[skills/chart-image-generator]] (0.273)、[[skills/image-analysis]] (0.272)、[[skills/data-anomaly-detection]] (0.262)、[[skills/biophysics-analyze-tissue-deformation-flow]] (0.223)、[[skills/cc-connect-send]] (0.210)、[[skills/math-ocr]] (0.190)、[[skills/run-experiment]] (0.180)、[[skills/remote-compute-modal]] (0.175)

## 反向链接
- [[skills/clip]]（可替代 (0.170)）
- [[skills/remote-compute-modal]]（相关 (0.175)）
- [[skills/ligandmpnn]]（可替代 (0.208)）
- [[skills/product-demand-research]]（相关 (0.168)）
- [[skills/data-anomaly-detection]]（相关 (0.262)）
- [[skills/drug-binding-site-definition]]（可替代 (0.301)）
- [[skills/cc-connect-send]]（相关 (0.210)）
- [[skills/math-ocr]]（相关 (0.190)）
- [[skills/image-analysis]]（相关 (0.272)）
- [[skills/biophysics-analyze-tissue-deformation-flow]]（相关 (0.223)）
- [[skills/bioimage-io-loader]]（相关 (0.171)）
