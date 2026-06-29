---
name: research-baseline-builder
description: Translate scientific questions into clear data inputs, outputs, and baseline workflows. Use when Codex needs to help researchers clarify what data goes in, what target or result should come out, how samples/labels/features are defined, and how to solve the resulting data problem through visualization, preprocessing, baseline design, training, evaluation, and reporting.
---

# Research Baseline Builder

## Overview

Use this skill to help a researcher turn a scientific question into a data problem with explicit inputs, outputs, and a baseline SOP. The goal is a defensible first experiment, not a model leaderboard.

Assume the user is a scientist or domain researcher. Do not over-explain their field. Help them make the data contract, baseline path, and evaluation boundary explicit.

The working shape is:

```text
Goal + Data + Data description
-> data-task recommendation
-> framework selection
-> visualization / preprocessing / baseline execution
-> interpretation report
-> check against the original scientific goal
```

## Core Rule

Do not start with models. First ask what goes in, what should come out, and what one sample means.

Always separate:

- scientific question: what the researcher wants to know;
- input: raw data, features, conditions, interventions, time points, images, text, spectra, tables, or sequences;
- output: label, measurement, effect, ranking, cluster, forecast, mechanism claim, or report;
- sample unit: what one row/sample/image/event/patient/material/paper represents;
- success criterion: what result would answer the scientific question;
- baseline: the simplest credible way to solve that data problem.

## Collaboration Style

- Treat domain claims as hypotheses to operationalize, not as material to lecture back.
- Ask only for missing information that changes the data task, split, metric, or baseline.
- Use the scientist's terms when they are clear; translate them into data roles beside the original wording.
- Be direct about unidentifiable causal claims, missing labels, leakage, weak ground truth, and small-sample limits.
- Avoid beginner tutorials unless the user asks. Give a research workflow, not a course note.

## Workflow

1. Restate the scientific question in one sentence.
2. Clarify the input-output contract:
   - research goal;
   - input data;
   - data description or field meaning;
   - expected output;
   - sample unit;
   - label/outcome/effect;
   - available features;
   - grouping/time/batch/source fields;
   - missing fields and assumptions.
3. Read `references/problem-to-data-routing.md` and choose the data-task family.
4. Read `references/framework-selection.md` and recommend the lightest sufficient framework.
5. Create a workspace with `scripts/init_research_baseline_workspace.py` when files are useful.
6. Write the SOP outputs in order:
   - `problem_definition.md`
   - `data_schema.csv`
   - `eda_plan.md`
   - `preprocess_plan.md`
   - `baseline_plan.md`
   - `train_eval_plan.md`
   - `baseline_report.md`
7. Only generate code after the input, output, sample unit, split rule, metric, and leakage risks are clear.
8. After results exist, read `references/goal-check.md` and check whether the output actually answers the original scientific goal. If not, decompose the task, revise the data question, or stop with the missing evidence.

If no data file is available, do not invent columns or write runnable training code. Produce the input-output contract, expected schema, baseline SOP, and the checks needed once data is provided.

## Baseline Ladder

After the input-output contract is clear, prefer this order:

1. sanity baseline: majority class, mean/median, last value, random, simple rule;
2. interpretable baseline: linear/logistic regression, Cox model, ARIMA, TF-IDF + linear model, simple statistical test;
3. strong classical baseline: RandomForest, XGBoost/LightGBM, SVM, mixed effects, propensity/matching, difference-in-differences;
4. neural or foundation baseline only when data size, modality, and evaluation justify it.

If the scientific question is causal, do not turn it into plain prediction without warning. Ask for intervention/exposure, outcome, confounders, timing, and identification assumptions.

## Standard SOP

Use this spine after the scientific question has been translated:

1. **Data visualization**: label distribution, missingness, feature distributions, group/time/batch balance, target leakage checks.
2. **Data preprocessing**: cleaning, units, outliers, missing values, normalization, encoding, duplicate handling, train/val/test split.
3. **Model building**: baseline ladder, feature set, assumptions, implementation package.
4. **Model training**: split protocol, seeds, cross-validation, hyperparameter boundary, logging.
5. **Model evaluation**: primary metric, secondary metrics, uncertainty, subgroup performance, error slices, calibration when relevant.
6. **Interpretation**: translate figures, metrics, and errors back to the scientific question.

## Guardrails

- Do not recommend random split when samples share patient, material, paper, lab, batch, site, time window, or source identity.
- Do not use post-outcome variables as features.
- Do not use row IDs, object IDs, filenames, source IDs, or database keys as predictive features unless the scientific question explicitly justifies them.
- Do not optimize only accuracy under imbalance.
- Do not call correlation an effect.
- Do not hide unavailable labels, small sample size, weak ground truth, or annotation noise.
- Do not overbuild. A clear baseline beats an impressive but uncheckable model.

## Output Contract

Report:

- scientific question;
- input-output contract;
- recommended data task and framework;
- data-task family and why;
- dataset schema and missing fields;
- split rule and leakage risks;
- baseline ladder;
- preprocessing and visualization checklist;
- training/evaluation plan;
- minimum files or scripts generated;
- what must be confirmed before stronger modeling.
