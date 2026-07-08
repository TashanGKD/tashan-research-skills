# find-science-skills Change Review

This file is a local review boundary for the current uncommitted quality-loop
work. It exists so the broad dirty worktree can be reviewed as a coherent
changeset before commit or push.

## Current Scope

- Retrieval quality improvements in `scripts/find_skills.py`.
- Static Wiki search improvements in `scripts/search_wiki.py`.
- Static Wiki generation and graph-view improvements in `scripts/build_wiki.py`.
- Release bench, holdout, and gap data under `data/`.
- Regression tests under `tests/`.
- Generated static artifacts: `wiki/search_index.json`, `data/skill_graph_view.json`, `site/graph.html`, and `wiki/gaps/`.
- Skill-facing docs in `SKILL.md`.

## Review Groups

### 1. Retrieval Ranking

- Files:
  - `scripts/find_skills.py`
  - `tests/test_find_skills.py`
  - `data/retrieval_bench.json`
  - `data/retrieval_bench_report.json`
- Main intent:
  - Fix hard ranking traps such as PDB retrieval vs AlphaFold prediction, IV/2SLS vs time-series econometrics, and method-specific scientific queries.
- Review focus:
  - Intent boosts should remain narrow.
  - New aliases should not cause broad false positives.
  - Release bench cases must use real installable skill IDs, never registry-gap placeholders.

### 2. Static Wiki Search And Explanations

- Files:
  - `scripts/search_wiki.py`
  - `scripts/build_wiki.py`
  - `tests/test_build_wiki.py`
  - `wiki/search_index.json`
- Main intent:
  - Keep Wiki search consistent with installer search.
  - Explain registry gaps in user-facing terms.
  - Preserve deterministic static outputs.
- Review focus:
  - Wiki-specific intent rules should mirror proven retrieval failures.
  - Gap pages should state why weak related skills are not installable recommendations.
  - Generated timestamps should stay stable across rebuilds from the same source graph.

### 3. Bench And Holdout Gate

- Files:
  - `scripts/bench_retrieval.py`
  - `tests/test_retrieval_bench.py`
  - `data/retrieval_bench.json`
  - `data/retrieval_holdout.json`
  - `data/retrieval_gaps.json`
  - `data/retrieval_bench_report.json`
  - `data/retrieval_holdout_report.json`
- Main intent:
  - Keep release bench for real installable skills.
  - Keep missing or unresolved coverage in holdout/gaps.
  - Make hard cases auditable with rationale and false-positive risks.
- Review focus:
  - `rationale` and `false_positive_risks` should be expanded gradually for hard cases.
  - Holdout registry-gap hits are not proof that the real skill exists.
  - Passing release bench is a local gate, not an external-service quality score.

### 4. Generated Static Artifacts

- Files:
  - `data/skill_graph_view.json`
  - `site/graph.html`
  - `wiki/search_index.json`
  - `wiki/gaps/*.md`
- Main intent:
  - Keep file-backed registry browsing/search usable without a database.
- Review focus:
  - Regenerate artifacts from the current source data before publishing.
  - Do not manually edit generated artifacts unless debugging a generation bug.
  - If source gap/bench data changes, rerun `build_wiki.py` and both retrieval bench commands.

## Required Local Gates

Run these before commit or push:

```powershell
python skills\find-science-skills\scripts\bench_retrieval.py
python skills\find-science-skills\scripts\bench_retrieval.py --holdout
$env:PYTEST_ADDOPTS='-p no:cacheprovider'; python -m pytest skills\find-science-skills\tests -q
python -m py_compile skills\find-science-skills\scripts\find_skills.py skills\find-science-skills\scripts\search_wiki.py skills\find-science-skills\scripts\bench_retrieval.py skills\find-science-skills\scripts\build_wiki.py
git diff --check -- skills/find-science-skills
```

Known local noise:

- Windows may emit a pytest atexit `PermissionError` while cleaning
  `pytest-current`; treat it as cleanup noise only when the pytest summary line
  still says all tests passed.
- Git may warn that LF will be replaced by CRLF; current checks have passed
  with these warnings.

## Current External-Service Score Policy

- External readiness baseline: `91/100` before the expert-review hardening pass.
- Current release-readiness gate after this pass:
  - release bench: `161/161` top-1/top-3;
  - holdout: `32/32` top-1/top-3;
  - holdout expected split: `8` real-skill cases and `24` registry-gap cases, with `find=4/12` and `wiki=4/12`;
  - pytest: `78 passed`;
  - static Wiki rebuild: `1457` pages, `1412` graph nodes, `17522` graph edges.
- Do not raise this score for simple re-runs, metadata-only additions, or passing
  the existing release bench.
- Score increases require evidence of at least one of:
  - a real ranking or recall defect fixed,
  - a hard/open-world bench issue caught and validated,
  - clearer user-facing gap explanations,
  - static artifact stability improvement,
  - a cleaner review/commit boundary.

## Commit Boundary Suggestion

When the user authorizes commit/push, prefer one conventional commit:

```text
test(find-science-skills): harden retrieval gate for release
```

The user authorized the commit/push boundary for this hardening pass. Keep the
commit scoped to `skills/find-science-skills`.
