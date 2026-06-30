#!/usr/bin/env python
"""Print Manim Agent LLM provider environment without exposing secrets."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderProfile:
    provider: str
    route: str
    label: str
    base_url: str
    model: str
    default_haiku_model: str
    default_sonnet_model: str
    default_opus_model: str
    auth_env_candidates: tuple[str, ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class TTSProfile:
    provider: str
    route: str
    label: str
    model: str
    voice: str
    auth_env_candidates: tuple[str, ...]
    extra_env: dict[str, str]
    notes: tuple[str, ...] = ()


PROFILES: dict[tuple[str, str], ProviderProfile] = {
    (
        "aliyun",
        "regular",
    ): ProviderProfile(
        provider="aliyun",
        route="regular",
        label="Aliyun DashScope / Bailian regular API",
        base_url="https://dashscope.aliyuncs.com/apps/anthropic",
        model="qwen3.7-plus",
        default_haiku_model="qwen3.6-flash",
        default_sonnet_model="qwen3.7-plus",
        default_opus_model="qwen3.7-plus",
        auth_env_candidates=("ALIYUN_DASHSCOPE_API_KEY", "DASHSCOPE_API_KEY", "ANTHROPIC_AUTH_TOKEN"),
    ),
    (
        "aliyun",
        "token-plan",
    ): ProviderProfile(
        provider="aliyun",
        route="token-plan",
        label="Aliyun Token Plan",
        base_url="https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic",
        model="qwen3.7-plus",
        default_haiku_model="qwen3.6-flash",
        default_sonnet_model="qwen3.7-plus",
        default_opus_model="qwen3.7-plus",
        auth_env_candidates=("ALIYUN_TOKEN_PLAN_API_KEY", "ANTHROPIC_AUTH_TOKEN"),
        notes=("Use the Token Plan endpoint only with a Token Plan key.",),
    ),
    (
        "aliyun",
        "coding-plan",
    ): ProviderProfile(
        provider="aliyun",
        route="coding-plan",
        label="Aliyun Coding Plan",
        base_url="https://coding.dashscope.aliyuncs.com/apps/anthropic",
        model="qwen3.7-plus",
        default_haiku_model="qwen3.6-flash",
        default_sonnet_model="qwen3.7-plus",
        default_opus_model="qwen3.7-plus",
        auth_env_candidates=("ALIYUN_CODING_PLAN_API_KEY", "ANTHROPIC_AUTH_TOKEN"),
        notes=("Use the Coding Plan endpoint only with a Coding Plan key.",),
    ),
    (
        "volcengine",
        "regular",
    ): ProviderProfile(
        provider="volcengine",
        route="regular",
        label="Volcengine Ark regular API",
        base_url="https://ark.cn-beijing.volces.com/api/compatible",
        model="deepseek-v4-pro-260425",
        default_haiku_model="deepseek-v4-pro-260425",
        default_sonnet_model="deepseek-v4-pro-260425",
        default_opus_model="deepseek-v4-pro-260425",
        auth_env_candidates=("ARK_API_KEY", "VOLCENGINE_API_KEY", "ANTHROPIC_AUTH_TOKEN"),
        notes=(
            "This profile targets Ark's Claude/Anthropic-compatible route, not the OpenAI-compatible /api/v3 route.",
        ),
    ),
    (
        "volcengine",
        "coding-plan",
    ): ProviderProfile(
        provider="volcengine",
        route="coding-plan",
        label="Volcengine Ark Coding Plan",
        base_url="https://ark.cn-beijing.volces.com/api/coding",
        model="ark-code-latest",
        default_haiku_model="ark-code-latest",
        default_sonnet_model="ark-code-latest",
        default_opus_model="ark-code-latest",
        auth_env_candidates=("ARK_API_KEY", "VOLCENGINE_API_KEY", "ANTHROPIC_AUTH_TOKEN"),
        notes=("Use the Coding Plan endpoint only with a Coding Plan key or matching Ark console configuration.",),
    ),
}

TTS_PROFILES: dict[tuple[str, str], TTSProfile] = {
    (
        "aliyun",
        "regular",
    ): TTSProfile(
        provider="aliyun",
        route="regular",
        label="Aliyun DashScope CosyVoice TTS",
        model="cosyvoice-v3-flash",
        voice="longanyang",
        auth_env_candidates=("DASHSCOPE_API_KEY", "ALIYUN_DASHSCOPE_API_KEY"),
        extra_env={"DASHSCOPE_API_BASE_URL": "https://dashscope.aliyuncs.com/api/v1"},
        notes=("Current upstream adapter natively supports DashScope CosyVoice.",),
    ),
    (
        "volcengine",
        "regular",
    ): TTSProfile(
        provider="volcengine",
        route="regular",
        label="Volcengine Speech Synthesis TTS",
        model="volcengine-tts",
        voice="zh_female_wanwanxiaohe_moon_bigtts",
        auth_env_candidates=("VOLCENGINE_TTS_API_KEY", "VOLCENGINE_TTS_ACCESS_TOKEN"),
        extra_env={
            "VOLCENGINE_TTS_APP_ID": "$env:VOLCENGINE_TTS_APP_ID",
            "VOLCENGINE_TTS_CLUSTER": "volcano_tts",
        },
        notes=(
            "Use a Volcengine speech-synthesis credential for narration; do not reuse an expired LLM-only key silently.",
            "If the upstream repo still has only the CosyVoice adapter, keep --no-tts or add the Volcengine adapter before production narration.",
        ),
    ),
}

ROUTE_ALIASES = {
    "ordinary": "regular",
    "normal": "regular",
    "payg": "regular",
    "api": "regular",
}


def canonical_route(route: str) -> str:
    return ROUTE_ALIASES.get(route, route)


def select_auth_env(profile: ProviderProfile, explicit_auth_env: str | None) -> str:
    if explicit_auth_env:
        return explicit_auth_env
    provider_specific = tuple(
        env_name
        for env_name in profile.auth_env_candidates
        if env_name not in {"ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"}
    )
    for env_name in provider_specific:
        if os.getenv(env_name):
            return env_name
    return provider_specific[0] if provider_specific else profile.auth_env_candidates[0]


def select_tts_auth_env(profile: TTSProfile, explicit_auth_env: str | None) -> str:
    if explicit_auth_env:
        return explicit_auth_env
    for env_name in profile.auth_env_candidates:
        if os.getenv(env_name):
            return env_name
    return profile.auth_env_candidates[0]


def build_payload(args: argparse.Namespace) -> dict[str, object]:
    route = canonical_route(args.route)
    key = (args.provider, route)
    if key not in PROFILES:
        known = ", ".join(f"{provider}:{profile_route}" for provider, profile_route in sorted(PROFILES))
        raise SystemExit(f"unsupported profile {args.provider}:{args.route}; known profiles: {known}")

    profile = PROFILES[key]
    auth_env = select_auth_env(profile, args.auth_env)
    model = args.model or profile.model
    base_url = args.base_url or profile.base_url

    return {
        "provider": profile.provider,
        "route": profile.route,
        "label": profile.label,
        "base_url": base_url,
        "model": model,
        "default_haiku_model": args.haiku_model or profile.default_haiku_model,
        "default_sonnet_model": args.sonnet_model or model or profile.default_sonnet_model,
        "default_opus_model": args.opus_model or model or profile.default_opus_model,
        "auth_token_env": auth_env,
        "auth_env_candidates": list(profile.auth_env_candidates),
        "force_claude_settings": "1",
        "notes": list(profile.notes),
        "secret_policy": "The script prints env-var references only and never prints API key values.",
    }


def build_tts_payload(args: argparse.Namespace) -> dict[str, object]:
    route = canonical_route(args.route)
    if route in {"token-plan", "coding-plan"}:
        route = "regular"
    key = (args.provider, route)
    if key not in TTS_PROFILES:
        known = ", ".join(f"{provider}:{profile_route}" for provider, profile_route in sorted(TTS_PROFILES))
        raise SystemExit(f"unsupported TTS profile {args.provider}:{args.route}; known profiles: {known}")

    profile = TTS_PROFILES[key]
    auth_env = select_tts_auth_env(profile, args.auth_env)
    return {
        "purpose": "tts",
        "provider": profile.provider,
        "route": profile.route,
        "label": profile.label,
        "model": args.model or profile.model,
        "voice": args.voice or profile.voice,
        "auth_token_env": auth_env,
        "auth_env_candidates": list(profile.auth_env_candidates),
        "extra_env": profile.extra_env,
        "notes": list(profile.notes),
        "secret_policy": "The script prints env-var references only and never prints API key values.",
    }


def quote_ps(value: str) -> str:
    escaped = value.replace("`", "``").replace('"', '`"')
    return f'"{escaped}"'


def render_env_ref_powershell(value: str) -> str:
    if value.startswith("$env:"):
        return value
    return quote_ps(value)


def render_powershell(payload: dict[str, object]) -> str:
    if payload.get("purpose") == "tts":
        return render_tts_powershell(payload)
    auth_env = str(payload["auth_token_env"])
    lines = [
        f"# Manim Agent LLM provider: {payload['label']}",
        "# Put the provider key in the referenced source env var first; no key value is printed here.",
        "$env:MANIM_AGENT_LLM_PROVIDER = " + quote_ps(str(payload["provider"])),
        "$env:MANIM_AGENT_LLM_ROUTE = " + quote_ps(str(payload["route"])),
        f"$env:ANTHROPIC_AUTH_TOKEN = $env:{auth_env}",
        f"$env:ANTHROPIC_API_KEY = $env:{auth_env}",
        "$env:ANTHROPIC_BASE_URL = " + quote_ps(str(payload["base_url"])),
        "$env:ANTHROPIC_MODEL = " + quote_ps(str(payload["model"])),
        "$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = " + quote_ps(str(payload["default_haiku_model"])),
        "$env:ANTHROPIC_DEFAULT_SONNET_MODEL = " + quote_ps(str(payload["default_sonnet_model"])),
        "$env:ANTHROPIC_DEFAULT_OPUS_MODEL = " + quote_ps(str(payload["default_opus_model"])),
        "$env:MANIM_AGENT_FORCE_CLAUDE_SETTINGS = " + quote_ps(str(payload["force_claude_settings"])),
    ]
    notes = payload.get("notes") or []
    lines.extend(f"# note: {note}" for note in notes)
    return "\n".join(lines) + "\n"


def render_tts_powershell(payload: dict[str, object]) -> str:
    auth_env = str(payload["auth_token_env"])
    lines = [
        f"# Manim Agent TTS provider: {payload['label']}",
        "# Put the provider TTS key in the referenced source env var first; no key value is printed here.",
        "$env:MANIM_AGENT_TTS_PROVIDER = " + quote_ps(str(payload["provider"])),
        "$env:MANIM_AGENT_TTS_ROUTE = " + quote_ps(str(payload["route"])),
        "$env:MANIM_AGENT_TTS_AUTH_TOKEN = " + f"$env:{auth_env}",
        "$env:MANIM_AGENT_TTS_MODEL = " + quote_ps(str(payload["model"])),
        "$env:MANIM_AGENT_TTS_VOICE = " + quote_ps(str(payload["voice"])),
    ]
    for name, value in dict(payload.get("extra_env") or {}).items():
        lines.append(f"$env:{name} = " + render_env_ref_powershell(str(value)))
    notes = payload.get("notes") or []
    lines.extend(f"# note: {note}" for note in notes)
    return "\n".join(lines) + "\n"


def render_shell(payload: dict[str, object]) -> str:
    if payload.get("purpose") == "tts":
        return render_tts_shell(payload)
    auth_env = str(payload["auth_token_env"])
    lines = [
        f"# Manim Agent LLM provider: {payload['label']}",
        "# Put the provider key in the referenced source env var first; no key value is printed here.",
        f"export MANIM_AGENT_LLM_PROVIDER={str(payload['provider'])!r}",
        f"export MANIM_AGENT_LLM_ROUTE={str(payload['route'])!r}",
        f"export ANTHROPIC_AUTH_TOKEN=\"${auth_env}\"",
        f"export ANTHROPIC_API_KEY=\"${auth_env}\"",
        f"export ANTHROPIC_BASE_URL={str(payload['base_url'])!r}",
        f"export ANTHROPIC_MODEL={str(payload['model'])!r}",
        f"export ANTHROPIC_DEFAULT_HAIKU_MODEL={str(payload['default_haiku_model'])!r}",
        f"export ANTHROPIC_DEFAULT_SONNET_MODEL={str(payload['default_sonnet_model'])!r}",
        f"export ANTHROPIC_DEFAULT_OPUS_MODEL={str(payload['default_opus_model'])!r}",
        f"export MANIM_AGENT_FORCE_CLAUDE_SETTINGS={str(payload['force_claude_settings'])!r}",
    ]
    notes = payload.get("notes") or []
    lines.extend(f"# note: {note}" for note in notes)
    return "\n".join(lines) + "\n"


def render_env_ref_shell(value: str) -> str:
    if value.startswith("$env:"):
        return f"${value.split(':', 1)[1]}"
    return repr(value)


def render_tts_shell(payload: dict[str, object]) -> str:
    auth_env = str(payload["auth_token_env"])
    lines = [
        f"# Manim Agent TTS provider: {payload['label']}",
        "# Put the provider TTS key in the referenced source env var first; no key value is printed here.",
        f"export MANIM_AGENT_TTS_PROVIDER={str(payload['provider'])!r}",
        f"export MANIM_AGENT_TTS_ROUTE={str(payload['route'])!r}",
        f"export MANIM_AGENT_TTS_AUTH_TOKEN=\"${auth_env}\"",
        f"export MANIM_AGENT_TTS_MODEL={str(payload['model'])!r}",
        f"export MANIM_AGENT_TTS_VOICE={str(payload['voice'])!r}",
    ]
    for name, value in dict(payload.get("extra_env") or {}).items():
        lines.append(f"export {name}={render_env_ref_shell(str(value))}")
    notes = payload.get("notes") or []
    lines.extend(f"# note: {note}" for note in notes)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print Manim Agent Claude Agent SDK provider env without printing secrets."
    )
    parser.add_argument("--provider", choices=["aliyun", "volcengine"], required=True)
    parser.add_argument("--purpose", choices=["llm", "tts"], default="llm")
    parser.add_argument(
        "--route",
        choices=["regular", "ordinary", "normal", "payg", "api", "token-plan", "coding-plan"],
        default="regular",
        help="Provider route. regular/ordinary/api aliases select the normal non-plan route.",
    )
    parser.add_argument("--model", help="Override ANTHROPIC_MODEL.")
    parser.add_argument("--base-url", help="Override ANTHROPIC_BASE_URL from the provider console.")
    parser.add_argument("--auth-env", help="Source environment variable name that already holds the API key.")
    parser.add_argument("--voice", help="Override TTS voice.")
    parser.add_argument("--haiku-model", help="Override ANTHROPIC_DEFAULT_HAIKU_MODEL.")
    parser.add_argument("--sonnet-model", help="Override ANTHROPIC_DEFAULT_SONNET_MODEL.")
    parser.add_argument("--opus-model", help="Override ANTHROPIC_DEFAULT_OPUS_MODEL.")
    parser.add_argument("--format", choices=["powershell", "shell", "json"], default="powershell")
    args = parser.parse_args()

    payload = build_tts_payload(args) if args.purpose == "tts" else build_payload(args)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.format == "shell":
        print(render_shell(payload), end="")
    else:
        print(render_powershell(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
