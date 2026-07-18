# Release Notes

## Initial Repository Release

Practical Course Producer turns executable software, research-tool, and
AI-assisted workflows into reproducible hands-on course projects whose final
deliverable is a video.

Included in this release:

- a four-gate `plan -> record -> render -> release` project contract;
- validation of relative paths, required planning artifacts, real source
  recordings, rendered media, and release evidence;
- versioned FFmpeg assembly with a machine-readable run manifest;
- deterministic media auditing with stream probes, SHA-256, silence detection,
  target-duration enforcement, and three representative frames;
- Volcengine HTTP Chunked v3 narration with timestamped subtitles, explicit
  missing/invalid API Key guidance, and an auditable Edge TTS fallback;
- a portable clean-checkout smoke and behavior, trigger, unit, and integration
  tests;
- explicit routing of concept-only animation to `manim-agent` and exclusion of
  ordinary editing, slide-only, marketing, and documentation-only requests.

No credentials, private recordings, generated videos, caches, or local absolute
paths are bundled. FFmpeg and FFprobe are required for render and release; real
course delivery also requires genuine operation recordings and human review of
teaching quality.
