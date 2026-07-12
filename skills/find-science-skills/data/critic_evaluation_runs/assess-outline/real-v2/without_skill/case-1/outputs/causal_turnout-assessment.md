# Outline assessment: Polling-Place Closures and Voter Turnout

## Overall assessment

This is a strong and unusually complete research outline. The research question, causal estimand, data, identification strategy, anticipated result, limitations, and replication plan are all visible. The main revision need is not broader coverage but greater precision about treatment construction and identification under staggered adoption. **Recommendation: proceed after targeted design clarification.**

## What is working

- The question is specific and consequential: the effect of polling-place closure on precinct-level turnout.
- The proposed contribution is differentiated from cross-sectional and local studies.
- The theory produces testable average and heterogeneous-effect predictions.
- The outline names the target population, period, outcome, treatment-related variables, and data sources.
- The identification section states core assumptions and connects them to event studies, placebos, balance checks, and sensitivity analyses.
- The conclusion and replication appendix set reasonable scope and reproducibility expectations.

## Priority issues

### 1. Define the treatment and estimand operationally

"Closure exposure" is currently ambiguous. State whether a closure means elimination of a precinct's prior polling location, reassignment to another location, net decline in locations within a geography, or a threshold increase in travel burden. Explain how precincts are tracked when boundaries change and what happens when a location later reopens or changes again. Specify whether the target is an average effect on treated precinct-election observations, an event-time effect, or another aggregation.

### 2. Make the staggered design explicit

County and election fixed effects alone do not establish that comparisons are valid under staggered timing, especially if effects vary across cohorts or over time. Name the estimator family, define the comparison group at each event time, state how standard errors will be clustered, and explain how treatment timing and repeated elections enter the panel.

### 3. Strengthen the identification argument

Event-study pre-trends are useful diagnostics but cannot by themselves establish parallel trends or rule out closure-timed confounding. The paper should explain the administrative process that generates closures, identify observable reasons for closure, and describe how concurrent reforms or turnout shocks will be measured or bounded. Clarify whether within-county changes are also within precinct and what variation identifies the estimate.

### 4. Resolve unit and denominator risks

The outcome denominator is voting-age citizens, but the data source and construction are not described. Explain geographic matching between election returns, polling-place records, precinct boundaries, and ACS measures; report uncertainty or interpolation where precinct-level denominators are estimated. Pre-specify treatment of precinct splits, merges, missing returns, mail voting, and election-type differences.

### 5. Align heterogeneity claims with measurement

Neighborhood income is a contextual measure, not necessarily voter income. Frame H2 and its interpretation accordingly, define the income measure and subgroup threshold, and test heterogeneity on a scale that permits a clear comparison. Avoid interpreting subgroup differences as individual-level mechanisms without additional evidence.

## Suggested outline revisions

1. Add a short treatment-and-estimand subsection before the identification discussion.
2. Separate the identification logic from diagnostics and robustness checks.
3. Add a data-construction subsection covering geographic linkage, boundary harmonization, denominator construction, and missingness.
4. In Results, distinguish the primary estimate, event-time dynamics, pre-specified heterogeneity, and exploratory analyses.
5. State which result is already estimated and which analyses remain planned; the current mix of present and future tense makes the project stage unclear.

## Bottom line

The outline is coherent and research-ready, but the causal claim depends on details that are still compressed into labels. A precise treatment definition, modern staggered-adoption specification, and transparent geographic linkage plan would make the argument assessable rather than merely plausible.
