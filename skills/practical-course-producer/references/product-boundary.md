# Product Boundary

## Defining test

Use this Skill when the lesson can be expressed as a bounded, executable workflow:

1. A real starting state exists.
2. The learner can observe at least one real action in a terminal, browser, GUI, or tool session.
3. The action produces an observable artifact or state change.
4. A real check verifies the result.

The generalization target is any workflow that satisfies those four conditions without changing the Skill code.

## Supported course families

- Software workflow: inspect, run, diagnose, change, diff, and retest.
- Research-tool workflow: import, configure, transform, export, and verify.
- AI-assisted workflow: enter the real tool, use short interactions, inspect generated artifacts, correct a weakness, and validate the result.
- Mixed explanation and demonstration: explain only enough concept to make the real workflow understandable.

## Route elsewhere

- Pure concepts, formulas, proofs, or technical animations with no executable workflow: use `manim-agent`.
- Slide-only teaching material: use a deck-generation Skill.
- Marketing, avatar, or brand videos: use the relevant media-production workflow.
- Ordinary trimming, color correction, denoising, or subtitle repair with no teaching design: use a video-editing workflow.
- Documentation-only requests: produce the requested document, not a fake course project.

Do not turn a concept-only request into a terminal demonstration merely to make this Skill apply.

## Completion boundary

A course is complete only when:

- `course-project.json` passes plan, record, render, and release;
- the operation evidence is real and includes a visible verification;
- the final video teaches the workflow without requiring intermediate Markdown;
- narration refers to observable actions rather than generic claims;
- the audit records media structure, hash, silence intervals, representative frames, and the remaining human-review boundary;
- no credential, private source, local user path, cache, or generated media enters the Skill package.

If real evidence cannot be captured, stop at the record gate. A complete plan is not a completed course video.
