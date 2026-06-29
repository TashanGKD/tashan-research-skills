---
name: scispark
description: Generate evidence-tracked research ideas through an arXiv-based, skill-native Scispark workflow. Use when Codex needs to turn a research keyword, question, paper set, Zotero/library material, or arXiv results into structured facts, testable hypotheses, an initial research idea, technical optimization, mechanism-of-action analysis, human-AI collaboration review, or optional academic slides. Also use when the user mentions Scispark, 科研想法生成, 研究假设生成, 机制优化, MoA, literature-backed idea generation, or 从关键词到研究方案.
---

# Scispark

## Overview

Use this skill to turn a research keyword or early topic into a staged, evidence-tracked research idea. This is a skill-native adaptation of the Tashan Scispark workflow: the current Codex model does the reasoning, and arXiv is the paper-search route.

The normal workflow does not require an external model API key or separate search product account.

## Resources

- `scripts/init_scispark_workspace.py`: create the standard output folders and starter files.
- `scripts/search_arxiv.py`: query arXiv and output normalized Scispark literature records.
- `references/arxiv-integration.md`: arXiv search, evidence status, and threshold rules.
- `references/stage-contracts.md`: required inputs and outputs for each stage.
- `assets/final_idea_template.md`: final research idea report structure.

## Workflow

1. Parse the user request into a keyword, domain, constraints, and target stage.
2. Create or identify the output directory. Default:

```text
03-AI笔记/scispark/{keyword}/
```

3. Read `references/arxiv-integration.md`, then run `scripts/search_arxiv.py` for literature search. Keep the actual query terms, source route, and status.
4. Read `references/stage-contracts.md` before writing stage files.
5. Execute stages in order unless the user asks for a target stage:
   - Stage 1: fact extraction
   - Stage 2: hypothesis generation
   - Stage 3: initial research idea
   - Stage 4: technical optimization + review
   - Stage 5: MoA optimization + review
   - Stage 6: human-AI collaboration integration + academic norm check
   - Stage 7: optional slide outline or Quarto/reveal.js source
6. Maintain `literature.csv` throughout. Every cited or candidate paper should have a row with title, source, stage, usage, and verification status.
7. Produce `{keyword}_final_idea.md` using `assets/final_idea_template.md`.

## Literature Thresholds

Use these as evidence-quality gates, not as rigid blockers:

| Level | Evidence | Action |
|---|---:|---|
| Ideal | 50+ relevant papers or records | Deep analysis |
| Standard | 30+ relevant papers or records | Normal workflow |
| Minimum | 15+ relevant papers or records | Proceed with limitation note |
| Below minimum | <15 records | Ask to broaden terms or stop before final claims |

When the user supplies a curated paper set, use it even if it is smaller, but label the scope.

## Review Rules

- Do not turn a keyword directly into a polished proposal without stage evidence.
- Separate facts, hypotheses, methods, mechanisms, and final synthesis.
- Assign stable hypothesis IDs `H1` to `H5`.
- Assign review problem IDs such as `S4-P1`, `S5-P1`, and `S6-P1`.
- For every strong claim in the final idea, point to a paper row, user-provided evidence, or an explicit limitation.
- Do not invent DOI, journal rank, impact factor, or full-text findings.
- Use arXiv records as `已核验` only when title, authors/year, arXiv ID, URL, and abstract are present and relevant. Otherwise mark `待核验`.
- If arXiv returns too few or weakly related records, broaden/refine the query before final claims and label the limitation.

## Output Contract

Report:

- output directory
- stages completed
- literature search route and status
- evidence count and threshold level
- top hypotheses
- final idea path
- limitations and next search/refinement step

For quick requests, stop at Stage 3 and say which later stages were skipped.
