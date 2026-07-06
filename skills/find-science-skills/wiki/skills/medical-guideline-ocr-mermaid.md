---
title: "medical-guideline-ocr-mermaid"
type: skill
tags: ["论文写作", "临床研究", "C"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
skill_id: "medical-guideline-ocr-mermaid"
quality_score: 61
tier: C
needs_review: false
source_repo: "jiongsn/medical-skills"
source_path: "skills/medical-guideline-ocr-mermaid/SKILL.md"
---

# medical-guideline-ocr-mermaid
## 一句话定位
[来源] 当任务是把医学指南 PDF 转成最终 Markdown，并需要先调用 PaddleOCR-VL 做 OCR/版面解析，再用 VLM 把指南中的图片、图表、算法图或流程图转换为 Mermaid，最后回填输出一个保留正文和表格的 Markdown 文件时使用。也适用于已有 PaddleOCR Markdown 但仍需抽取图片并转 Mermaid 的情况。

## 检索线索
- 能力组：论文写作
- 功能家族：表达发表
- 学科：医学临床 / 临床研究
- 中文关键词：医学指南OCR, PaddleOCR-VL, Mermaid图表生成, VLM视觉语言模型, PDF版面解析, 医学流程图识别, Markdown回填, 临床指南数字化, 算法图转换, 图表OCR提取

## 质量信号
| 指标 | 值 |
| --- | --- |
| 质量分 | 61 |
| Tier | C |
| 深评 | 未深评 |
| 来源仓库数 | 1 |
| stars | 1 |
| 待复核 | 否 |

## 获取方式
- 仓库：`jiongsn/medical-skills`
- 路径：`skills/medical-guideline-ocr-mermaid/SKILL.md`

## 图关系
- 可替代：[[skills/paper-to-course]] (0.162)、[[skills/survey-writer]] (0.162)、[[skills/empirical-paper]] (0.160)
- 配套：[[skills/medical-guideline-parser-v2]]
- 相关：[[skills/nianan-scientificfig-skills]] (0.342)、[[skills/sci-figure]] (0.286)、[[skills/figure-spec]] (0.282)、[[skills/paper-illustration]] (0.223)、[[skills/survey-director]] (0.208)、[[skills/nature-experiment-log]] (0.200)、[[skills/paper-figure]] (0.198)、[[skills/academic-pipeline-cn]] (0.188)

## 反向链接
- [[skills/paper-to-course]]（可替代 (0.162)）
- [[skills/figure-description]]（相关 (0.158)）
- [[skills/nature-experiment-log]]（相关 (0.200)）
- [[skills/figure-spec]]（相关 (0.282)）
- [[skills/sci-figure]]（相关 (0.286)）
- [[skills/paper-review]]（相关 (0.123)）
- [[skills/paper-illustration]]（相关 (0.223)）
- [[skills/auto-deep-research]]（相关 (0.188)）
- [[skills/multi-agent-research]]（相关 (0.177)）
- [[skills/nianan-scientificfig-skills]]（相关 (0.342)）
- [[skills/medical-guideline-parser-v2]]（配套）
