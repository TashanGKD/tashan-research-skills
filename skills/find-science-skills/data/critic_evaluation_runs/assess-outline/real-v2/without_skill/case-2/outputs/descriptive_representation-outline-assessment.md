# Outline assessment: Who Receives Constituent Responses?

## Overall assessment

This is a well-structured descriptive study with a clear question, defined outcome, multi-city contribution, and appropriately limited causal language. Its main vulnerability is measurement comparability: archived service-request systems may differ substantially in who can submit, what counts as a response, and what is recorded. **Recommendation: proceed after strengthening the measurement and selection framework.**

## What is working

- The abstract states the question, motivation, data scale, analytical approach, contribution, and main descriptive finding.
- The distinction between acknowledgment and substantive response improves construct validity.
- The population, years, outcome window, predictors, and unit-level context are mostly clear.
- The proposed multilevel model matches the goal of summarizing conditional associations across cities.
- The discussion explicitly avoids causal interpretation and recognizes that only submitted requests are observed.
- The reproducibility appendix anticipates harmonization documentation and legal sharing constraints.

## Priority issues

### 1. Define the inferential population accurately

The observed population is service requests present in the participating cities' archives, not all residents or all constituent requests. Revise the population statement and explain city selection, archive coverage, duplicate requests, excluded channels, and whether repeat submitters can be identified. Discuss how digital access and local reporting practices shape entry into the dataset.

### 2. Establish cross-city outcome comparability

"Substantive response" needs a coding rule that can survive different municipal systems. Specify whether the response is text, a status transition, completed work, direct contact, or another event. Report validation procedures, coder agreement if manual classification is used, and city-level differences in record retention or automated updates.

### 3. Separate description from explanation

Issue type and neighborhood disadvantage may be associated with request complexity, agency jurisdiction, service standards, channel choice, and backlog. Present adjusted probabilities as standardized descriptive comparisons, not explanations of why responses differ. State which variables are adjustment factors and which comparisons are the primary reported quantities.

### 4. Clarify the hierarchy and uncertainty

Describe the nesting structure: requests may be nested within neighborhoods, agencies, cities, and years, with repeat requesters potentially adding another dependence layer. Explain the random or fixed effects, uncertainty intervals, treatment of sparse issue-city cells, and whether the 30 cities are the full target set or a sample from a broader population.

### 5. Add missing-data and classification diagnostics

The outline should address missing neighborhood matches, missing response timestamps, inconsistent issue taxonomies, and requests transferred across departments. Show how harmonized categories are constructed and whether conclusions change under alternative mappings.

## Suggested outline revisions

1. Add a "Coverage and selection" subsection to Data.
2. Add a "Measurement and harmonization" subsection defining requests, responses, channels, and issue categories.
3. Open Analysis with unadjusted city-by-issue distributions and sample denominators before model-based probabilities.
4. Pre-specify one primary comparison and label the remaining subgroup analyses as secondary.
5. Expand robustness checks to include missingness bounds, alternative category mappings, and exclusion of cities with noncomparable response logging.

## Bottom line

The outline is coherent and appropriately descriptive. Its publishability will depend less on a more elaborate model than on proving that the same outcome and request categories mean sufficiently similar things across all 30 cities.
