# Manim Agent environment template for Windows PowerShell.
# Copy the needed lines into a local shell or private env file, then replace
# placeholder values outside this repository. Do not commit real API keys.

# Repository path used by this Codex skill.
$env:MANIM_AGENT_REPO = "D:\数字分身\manim-agent"

# Option A: Aliyun DashScope / Bailian for the LLM layer.
# $env:ALIYUN_DASHSCOPE_API_KEY = "<aliyun-dashscope-key>"
# python ".\scripts\configure_manim_provider.py" --provider aliyun --route regular --format powershell

# Option B: Volcengine Ark for the LLM layer.
# $env:ARK_API_KEY = "<volcengine-ark-key>"
# python ".\scripts\configure_manim_provider.py" --provider volcengine --route regular --format powershell

# Optional Aliyun CosyVoice narration. This is natively supported by the current
# upstream manim-agent TTS adapter.
# $env:DASHSCOPE_API_KEY = "<dashscope-cosyvoice-key>"
# python ".\scripts\configure_manim_provider.py" --provider aliyun --purpose tts --format powershell

# Optional Volcengine narration profile. Use a speech-synthesis credential, not
# an LLM-only Ark key unless the provider console explicitly grants TTS access.
# $env:VOLCENGINE_TTS_API_KEY = "<volcengine-tts-key>"
# $env:VOLCENGINE_TTS_APP_ID = "<volcengine-tts-app-id>"
# python ".\scripts\configure_manim_provider.py" --provider volcengine --purpose tts --format powershell

# Validate without printing secret values.
# python ".\scripts\check_manim_agent_env.py" --repo $env:MANIM_AGENT_REPO
