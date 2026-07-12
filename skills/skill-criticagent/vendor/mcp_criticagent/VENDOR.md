# Vendored MCP-CriticAgent evaluation kernel

This directory contains an exact copy of the original Agent Skill evaluation
kernel from `TashanGKD/MCP-CriticAgent`. It is bundled so that
`skill-criticagent` works when this research-skills repository is mounted on a
different machine without an absolute local path or a second checkout.

- Upstream repository: `https://github.com/TashanGKD/MCP-CriticAgent`
- Upstream base commit: `6503c65edb43e9036cb2bba26d00623f96f0511c`
- Source branch at import: `feat/agent-skill-evaluator-core`
- Staged source tree at import: `cc6a5c2da95e3d1f60a855c6fd65f4c85fad85a7`
- License: MIT; see `LICENSE`
- Local integration changes: none inside `src/core/skill_*.py`

`manifest.json` records SHA-256 hashes for every copied runtime file. Update
the vendored kernel only by copying a reviewed upstream version and refreshing
that manifest; do not patch the copied evaluator logic in place.
