# Reproducible CriticAgent runs

Each directory contains the exact skill snapshot, `evals/evals.json`,
`runs.json`, and `decisions.json` used for a formal evaluation. The model
outputs are inputs to the deterministic CriticAgent kernel; replaying does
not call a model or change the recorded answers.

From the repository root, replay one skill with the bundled kernel:

```powershell
$id = "research-project-orienter"
$run = "skills/find-science-skills/data/critic_evaluation_runs/$id"
python skills/skill-criticagent/scripts/grade_runs.py `
  "$run/$id" "$run/runs.json" --output "$run/behavior.replay.json"
python skills/skill-criticagent/scripts/grade_triggers.py `
  "$run/$id" "$run/decisions.json" --output "$run/trigger.replay.json"
```

`expected_hashes.json` records the exact SHA-256 values produced during the
original formal run and verified again after the kernel was bundled. The raw
JSON hash includes `skill_path`, so a checkout at another absolute path should
compare the parsed result after removing that provenance field rather than
expecting a byte-identical file.
