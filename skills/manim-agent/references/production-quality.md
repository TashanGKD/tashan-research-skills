# Production Quality

Use this file before generating or reviewing Manim teaching videos.

## Reuse Existing Production Rules

The repo contains detailed production skills and references under:

```text
<path-to-manim-agent>\plugins\manim-production\
```

When working inside the repo, prefer those rules over generic Manim habits:

- `skills/manim-production/SKILL.md`: production router
- `skills/scene-plan/SKILL.md`: beat structure and learning sequence
- `skills/scene-build/SKILL.md`: implementation and render loop
- `skills/scene-direction/SKILL.md`: visual direction
- `skills/layout-safety/SKILL.md`: frame-safe layout checks
- `skills/narration-sync/SKILL.md`: beat-aligned narration
- `skills/render-review/SKILL.md`: rendered frame review
- `skills/intro-outro/SKILL.md`: branded intro/outro

Relevant references:

- `references/scene-patterns.md`
- `references/math-visualization-guidelines.md`
- `references/narration-guidelines.md`
- `references/spatial-composition.md`
- `references/animation-craft.md`
- `references/render-quality.md`
- `references/style-3b1b.md`
- `references/anti-patterns.md`
- `references/build-anti-patterns.md`
- `references/planning-anti-patterns.md`

Load only the files needed for the current task.

## Task Types

Classify each request before generation:

- `quick-demo`: short visual demo, minimal narration.
- `concept-explainer`: intuition, analogy, progressive reveal.
- `proof-walkthrough`: assumptions, transformations, conclusion.
- `function-visualization`: axes, parameter changes, graph behavior.
- `geometry-construction`: objects, labels, angle/length relations, construction steps.
- `presentation`: concise, polished, less derivation.

Use this classification to choose pacing, visual density, and narration style.

## Teaching Rules

- One beat should introduce one main idea.
- A screen should not become a paragraph. Prefer short labels, formula focus, and visual relationships.
- Establish spatial relationships before animating transformations.
- Highlight only the changing part of a formula.
- Use color semantically and consistently.
- Keep Chinese narration natural and synchronized with visible action.
- Do not narrate future visual elements before they appear.
- Do not read long on-screen text aloud.

## Manim Implementation Rules

- Prefer `scene.py` and one main `GeneratedScene` unless the task requires multiple scenes.
- Prefer reusable components from `plugins/manim-production/components/` when available.
- For CJK text, use the repo text helpers when working inside the production plugin context.
- Avoid large piles of absolute coordinates. Use object relationships, groups, layouts, and named constants.
- Use `Wait()` deliberately for comprehension, not as filler.
- Keep camera framing and margins stable.
- Make formulas readable at video resolution.

## Quality Gates

Before rendering:

- Confirm the scene class and file match the command.
- Check that no long text block will overflow the frame.
- Check that formula labels and object colors have stable meaning.
- Check that every beat has a visible purpose.

After rendering:

- Confirm the MP4 exists.
- Sample frames or enable `--render-review` for strict runs.
- Check for overlap, cropped text, unreadable formulas, empty frames, or narration mismatch.
- If the video is for a user-facing delivery, prefer one additional review pass over reporting success too early.

## What Not To Do

- Do not downgrade a video request into a static diagram.
- Do not produce only a code snippet when the user asked for an MP4.
- Do not overfill screens with text.
- Do not mix English labels into a Chinese teaching video unless the concept requires it.
- Do not claim TTS worked when the run used `--no-tts`.
- Do not say "the pipeline should generate" as if it generated; verify the artifact.
