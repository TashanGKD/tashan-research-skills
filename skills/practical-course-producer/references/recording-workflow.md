# Recording Workflow

## When to read this

Read this reference only when the requested deliverable includes real terminal,
browser, CLI, or AI-tool recording.

## Browser terminal pattern

Use a local browser terminal when recording the foreground desktop would disrupt
the user. The backend must run the real shell process; the browser only mirrors
input and output.

Capture these scenes when they are relevant:

- environment and working-directory check;
- normal entry into the interactive tool;
- a short creation request;
- file or output inspection;
- a real validator or sample failure;
- one focused correction;
- validator rerun or sample retest;
- final artifact preview.

Do not use a non-interactive long prompt when the lesson claims to demonstrate
interactive work. Do not print prepared output into a terminal.

## Interaction plan

Group the workflow into a few meaningful turns. For each turn record:

- the exact short user message;
- the reason it is needed;
- the expected tool action, not a fabricated response;
- the file, command, or visual evidence used to judge it.

The user message should sound like something a person can remember and type.
Split only when the next turn depends on inspecting the previous result.

## Screen behavior

- Hold a typed prompt long enough to explain it before pressing Enter.
- Scroll downward slowly while output streams; avoid purposeless up/down motion.
- Keep commands and important output fully visible.
- Use local content zoom; keep titles, framing, and adjacent explanation fixed.
- Preserve enough time to read results. Speed up only verified dead waiting.

## Evidence log

For every recording keep a small record of source path, start/end time, command or
interaction shown, whether it is real, and the acceptance evidence. Do not store
credentials or full private terminal logs in that record.
