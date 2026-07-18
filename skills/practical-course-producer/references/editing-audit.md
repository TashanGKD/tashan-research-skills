# Editing And Audit

## When to read this

Read this reference only when editing media or verifying a rendered course.

## Version discipline

Keep meaningful outputs versioned and preserve short check clips around changed
regions. Never overwrite the accepted baseline.

When only audio changes, copy the previous video stream and encode only the new
audio. Compare video stream hashes before claiming the visuals are unchanged.

```powershell
ffmpeg -v error -i previous.mp4 -map 0:v:0 -f streamhash -hash sha256 -
ffmpeg -v error -i revised.mp4  -map 0:v:0 -f streamhash -hash sha256 -
```

## Frame checks

Extract consecutive frames around the suspect timestamp. Prefer deterministic
frame selection when accurate seeking matters.

Check:

- visible content matches the narration;
- key commands and code are not cropped;
- zoom targets only the discussed content;
- titles and side explanations remain fixed and complete;
- the viewer has enough reading time;
- transitions do not expose stale or unrelated content.

## Audio checks

Use `ffprobe` for stream duration and `silencedetect` or `volumedetect` for the
changed region. Leave a short lead-in before every regenerated sentence. Do not
accelerate narration to fit a scene.

```powershell
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 output.mp4
ffmpeg -hide_banner -i output.mp4 -af "silencedetect=noise=-40dB:d=1.5" -f null NUL
```

## Script repair

For narration that sounds read aloud, replace abstract claims with observable
actions. Keep one idea per sentence. Regenerate only the affected segment and
reuse accepted audio/video elsewhere.

If TTS misreads a technical filename, change the spoken wording rather than
forcing letter-by-letter pronunciation.

## Audit report

Record the baseline, exact changed region, build command, output path, frame and
audio evidence, remaining issues, and verdict. A file existing is not proof that
the course is correct.
