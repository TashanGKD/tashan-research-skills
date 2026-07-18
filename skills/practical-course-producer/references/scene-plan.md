# Scene Plan

Use the packaged builder when real source recordings already exist and the
task is to assemble a reproducible first cut. Source paths are relative to the
JSON plan file.

```json
{
  "slug": "my-practical-course",
  "video": {
    "width": 1280,
    "height": 720,
    "fps": 30,
    "sample_rate": 48000
  },
  "scenes": [
    {
      "id": "opening",
      "source": "recordings/opening.mp4",
      "start": 0,
      "duration": 4.5
    },
    {
      "id": "first-check",
      "source": "recordings/terminal.mp4",
      "start": 12.2,
      "narration": "audio/first-check.wav",
      "captions": "audio/first-check.timeline.json",
      "background": "frames/terminal-frame.png",
      "content_box": { "x": 56, "y": 126, "width": 860, "height": 484 }
    }
  ]
}
```

Run from any directory:

```powershell
python scripts/build_course_video.py course-plan.json --output-dir outputs
```

Before rendering, generate the narration referenced by a scene. Volcengine TTS
HTTP Chunked v3 is primary and Edge TTS is the fallback. Both paths produce
provider-backed sentence timing data, and the timeline records which provider
actually ran:

Set `VOLCENGINE_TTS_API_KEY` in the environment. When it is missing or rejected,
obtain or replace it at
`https://console.volcengine.com/speech/new/setting/apikeys?projectName=default`;
never store it in the scene plan or ask the user to paste it into chat.

```powershell
python scripts/synthesize_narration.py narration.md `
  --output audio/narration.mp3 `
  --timeline audio/narration.timeline.json
```

The builder validates every source and trim boundary before rendering. It
normalizes scene dimensions, frame rate, pixel format, audio sample rate, and
channel count; sources without audio receive silence. An optional `narration`
path replaces source audio. When `duration` is omitted, narration duration sets
the scene duration and the final real video frame is held as needed; narration
is never accelerated. An explicit duration shorter than the narration is
rejected. The builder writes these timings to the sibling `.run.json` manifest.
It never fabricates terminal content or mutates source recordings.

Set `captions` to the sentence timeline emitted by
`synthesize_narration.py`. The builder burns readable bottom-center Chinese
captions with a bounded dark background and records the caption count in the
run manifest. Caption timings that exceed the scene duration are rejected.

When a scene has `background`, its real source video is scaled into the required
`content_box` while the full output frame stays fixed. Use this for a persistent
course title or explanation panel; the box must fit inside the output frame.
