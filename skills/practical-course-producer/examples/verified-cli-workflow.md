# Verified CLI Workflow Example

## Request

> Make a short course showing how to run a command-line check, inspect the
> result, correct one failure, and rerun the same check successfully.

This request belongs to Practical Course Producer because it has a starting
state, visible terminal actions, a changed artifact, and a real retest. A
concept-only explanation of the command does not belong here.

## Run the public project

The repository includes a credential-free fixture under
`tests/fixtures/course-project/`. Its recording is intentionally absent so the
record gate fails until genuine media is supplied. The portable smoke creates a
temporary test recording, advances the copied project through all four gates,
and deletes the generated media afterward:

```powershell
python scripts/smoke_course_project.py
```

Expected evidence:

- `status` is `pass` and `final_gate` is `release`;
- a versioned MP4 and run manifest are produced in the temporary project;
- `audit.md` and three representative frames are generated;
- `checkout_unchanged` is `true`.

The test pattern proves orchestration and media auditing only. A publishable
course must replace it with a real terminal or tool recording, aligned
narration, and human review of teaching accuracy and readability.

## Apply it to a real project

1. Copy `assets/course-project.json` outside the installed Skill directory.
2. Fill in the course metadata and relative artifact paths.
3. Create the four planning files, then pass the `plan` gate.
4. Record the real workflow and reference it from the scene plan.
5. Advance through `record`, `render`, and `release` without bypassing a gate.
6. Review the final video and generated audit before delivery.
