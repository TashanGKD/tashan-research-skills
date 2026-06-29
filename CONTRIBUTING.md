# Contributing

This repository hosts research skills, not one-off task outputs. Keep changes small, reviewable, and tied to a real research workflow.

## Pull request standard

- State which skill is changed and why.
- Keep each PR focused on one skill or one cross-repo maintenance concern.
- Update `SKILL.md` when behavior, triggers, inputs, outputs, or dependencies change.
- Put reusable code in `scripts/`, reusable wording in `templates/`, and reference material in `references/`.
- Do not commit generated run folders, private papers, raw model logs, local caches, or credentials.
- Add or update a smoke test when a script changes.

## Skill quality bar

A skill should answer these questions without requiring readers to inspect all internals:

- When should this skill be used?
- What inputs does it accept?
- What outputs should it produce?
- What local files, tools, APIs, or environment variables does it depend on?
- What must never be written to disk or shown to the user?
- How can a maintainer verify it still works?

## Review checklist

- The skill has one clear job.
- The README or skill index points to the right entrypoint.
- Secret handling is explicit.
- Failure modes are documented.
- Scripts can be run from the skill folder or document their expected working directory.
- New files are named predictably and do not hide important behavior in generated blobs.
