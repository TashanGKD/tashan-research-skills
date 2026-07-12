#!/usr/bin/env python3
"""Build an optional, resumable CriticAgent scorecard for the science catalog."""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import importlib
import json
import os
import pathlib
import sys
import tempfile
import time
import urllib.error
import urllib.request
from typing import Callable

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from finalize_critic_scores import SCHEMA, finalize_record  # noqa: E402


SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = SKILL_DIR / "data" / "science_skill_catalog.json"
DEFAULT_OUTPUT = SKILL_DIR / "data" / "science_skill_critic_scores.json"
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "deepseek-v4-flash-260425"
RUBRIC_VERSION = "source-review-v2"
DIMENSIONS = (
    "instruction_quality",
    "task_actionability",
    "safety",
    "trigger_clarity",
    "package_maintainability",
)

SOURCE_RUBRIC = """You are reviewing the quality of an Agent Skill. Evaluate the complete
SKILL.md and the real directory manifest below. Agent Skills may be guidance-only,
executable, or hybrid. A guidance skill does not need scripts when its instructions
are sufficient for the host model. Penalize a missing dependency only when the
instructions require it and the manifest proves it is absent. Do not penalize extra
frontmatter fields by themselves.

Score five dimensions totaling 100:
- instruction_quality 0-25: goal, inputs, outputs, steps, and boundaries
- task_actionability 0-25: executable or reliably usable for its declared skill type
- safety 0-20: higher is safer; high-risk domains require explicit safeguards
- trigger_clarity 0-15: clear positive and near-miss activation boundaries
- package_maintainability 0-15: references, dependencies, structure, compatibility

Return strict JSON only with this shape:
{"instruction_quality":0,"task_actionability":0,"safety":0,
"trigger_clarity":0,"package_maintainability":0,"overall":0,
"verdict":"recommend|fix_first|reject","confidence":"high|medium|low",
"skill_type":"guidance|executable|hybrid","strengths":[],"risks":[],"evidence":[]}
overall must equal the five dimensions. Cite at least two concrete pieces of evidence.
Do not treat document length as quality.
"""

METADATA_RUBRIC = """You are triaging an Agent Skill from registry metadata only. The
original SKILL.md is unavailable, so do not infer implementation, safety, package
integrity, or behavior. Estimate only whether the stated task appears clear and useful.
Return the same strict JSON shape as requested below, set confidence to low, include
"source unavailable" in risks, and avoid a recommend verdict unless the metadata itself
is unusually complete. When safety or package quality is unknown, use a neutral midpoint
rather than zero. This score is provisional and must not be presented as a full source
review.
"""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def atomic_write_json(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def resolve_source(skill: dict, source_root: pathlib.Path | None) -> pathlib.Path | None:
    if source_root is None:
        return None
    repository = skill.get("source_repository")
    relative = skill.get("source_path")
    if not repository or not relative:
        return None
    path = source_root / repository.replace("/", "__") / relative
    return path if path.is_file() else None


def directory_manifest(skill_md: pathlib.Path, limit: int = 400) -> list[str]:
    entries = []
    paths = sorted(
        skill_md.parent.rglob("*"),
        key=lambda path: (
            path.name.lower() != "skill.md",
            path.relative_to(skill_md.parent).as_posix().casefold(),
        ),
    )
    for path in paths:
        if not path.is_file():
            continue
        entries.append(path.relative_to(skill_md.parent).as_posix())
        if len(entries) == limit:
            entries.append("[additional files omitted from manifest]")
            break
    return entries


def metadata_prompt(skill: dict) -> str:
    fields = {
        key: skill.get(key)
        for key in (
            "id",
            "name",
            "summary",
            "task",
            "domain",
            "subdomain",
            "stage",
            "function",
            "source_repository",
            "source_path",
        )
    }
    return METADATA_RUBRIC + "\n\n" + SOURCE_RUBRIC + "\n\nMetadata:\n" + json.dumps(
        fields, ensure_ascii=False, indent=2
    )


def source_prompt(skill_md: pathlib.Path, content: str) -> str:
    return (
        SOURCE_RUBRIC
        + "\n\nDirectory manifest:\n"
        + json.dumps(directory_manifest(skill_md), ensure_ascii=False, indent=2)
        + "\n\nComplete SKILL.md:\n"
        + content
    )


def extract_json_object(value: str) -> dict:
    start = value.find("{")
    end = value.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("model response did not contain a JSON object")
    return json.loads(value[start : end + 1])


def normalize_review(review: dict, *, evidence_level: str) -> dict:
    normalized = {}
    limits = dict(zip(DIMENSIONS, (25, 25, 20, 15, 15)))
    for field, maximum in limits.items():
        value = review.get(field)
        if not isinstance(value, (int, float)):
            raise ValueError(f"model review missing numeric {field}")
        normalized[field] = max(0, min(maximum, int(round(value))))
    normalized["critic_content_score"] = sum(normalized.values())
    verdict = (
        review.get("verdict")
        if review.get("verdict") in {"recommend", "fix_first", "reject"}
        else "fix_first"
    )
    if normalized["critic_content_score"] < 30:
        verdict = "reject"
    elif evidence_level == "metadata_only" and verdict == "recommend":
        verdict = "fix_first"
    normalized["critic_verdict"] = verdict
    confidence = review.get("confidence")
    if evidence_level == "metadata_only":
        confidence = "low"
    normalized["critic_confidence"] = (
        confidence if confidence in {"high", "medium", "low"} else "low"
    )
    normalized["critic_skill_type"] = (
        review.get("skill_type")
        if review.get("skill_type") in {"guidance", "executable", "hybrid"}
        else "guidance"
    )
    for field in ("strengths", "risks", "evidence"):
        values = review.get(field)
        normalized[field] = (
            [str(item)[:500] for item in values[:4]] if isinstance(values, list) else []
        )
    return normalized


class ArkChatClient:
    def __init__(
        self,
        api_key: str,
        *,
        model: str,
        base_url: str,
        timeout: int,
        retries: int,
    ):
        self.api_key = api_key
        self.model = model
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.timeout = timeout
        self.retries = retries

    def complete(self, prompt: str) -> tuple[str, dict]:
        body = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
                last_error = RuntimeError(f"Ark HTTP {exc.code}: {detail}")
                if exc.code not in {408, 429, 500, 502, 503, 504}:
                    raise last_error from exc
            except (TimeoutError, urllib.error.URLError) as exc:
                last_error = exc
            if attempt < self.retries:
                time.sleep(min(2**attempt, 8))
        else:
            raise RuntimeError(f"Ark request failed after retries: {last_error}")
        message = payload["choices"][0]["message"].get("content") or ""
        return message, payload.get("usage") or {}


def load_validator(critic_root: pathlib.Path | None) -> Callable | None:
    if critic_root is None:
        return None
    sys.path.insert(0, str(critic_root))
    module = importlib.import_module("src.core.skill_validator")
    return module.validate_skill_dir


def package_evidence(skill_md: pathlib.Path | None, validator: Callable | None) -> dict:
    if skill_md is None:
        return {"critic_package_status": "source_unavailable", "errors": [], "warnings": []}
    if validator is None:
        return {"critic_package_status": "not_checked", "errors": [], "warnings": []}
    result = validator(skill_md.parent, strict=True)
    return {
        "critic_package_status": "pass" if result.valid else "fail",
        "errors": result.errors[:12],
        "warnings": result.warnings[:12],
    }


def score_one(
    skill: dict,
    *,
    source_root: pathlib.Path | None,
    validator: Callable | None,
    client: ArkChatClient,
) -> dict:
    source = resolve_source(skill, source_root)
    if source:
        content = source.read_text(encoding="utf-8-sig", errors="replace")
        evidence_level = "full_source"
        prompt = source_prompt(source, content)
        source_hash = sha256_text(content)
    else:
        content = ""
        evidence_level = "metadata_only"
        prompt = metadata_prompt(skill)
        source_hash = None

    started = time.monotonic()
    response, usage = client.complete(prompt)
    review = normalize_review(extract_json_object(response), evidence_level=evidence_level)
    raw_record = {
        "id": skill["id"],
        "critic_content_score": review.pop("critic_content_score"),
        "critic_evidence_level": evidence_level,
        "critic_model": client.model,
        "critic_rubric_version": RUBRIC_VERSION,
        "critic_source_sha256": source_hash,
        **package_evidence(source, validator),
        **review,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "usage": usage,
    }
    return finalize_record(raw_record)


def record_is_current(
    skill: dict,
    record: dict | None,
    *,
    model: str,
    source_root: pathlib.Path | None,
    catalog_unchanged: bool,
) -> bool:
    if not record:
        return False
    if record.get("critic_model") != model:
        return False
    if record.get("critic_rubric_version") != RUBRIC_VERSION:
        return False
    source = resolve_source(skill, source_root)
    if source is None:
        return (
            catalog_unchanged
            and record.get("critic_evidence_level") == "metadata_only"
        )
    content = source.read_text(encoding="utf-8-sig", errors="replace")
    return (
        record.get("critic_evidence_level") == "full_source"
        and record.get("critic_source_sha256") == sha256_text(content)
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成可选 CriticAgent 科研技能评分旁车。")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--source-root", default=os.getenv("SCIENCE_SKILL_SOURCE_ROOT"))
    parser.add_argument("--critic-root", default=os.getenv("MCP_CRITICAGENT_ROOT"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=os.getenv("ARK_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--id", action="append", dest="ids")
    parser.add_argument("--no-resume", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        raise SystemExit("ARK_API_KEY is required and is never written to the scorecard")
    catalog_path = pathlib.Path(args.catalog)
    output_path = pathlib.Path(args.output)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog_hash = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
    source_root = pathlib.Path(args.source_root) if args.source_root else None
    critic_root = pathlib.Path(args.critic_root) if args.critic_root else None
    selected = catalog["skills"]
    if args.ids:
        wanted = set(args.ids)
        selected = [skill for skill in selected if skill["id"] in wanted]
    if args.limit is not None:
        selected = selected[: args.limit]

    existing = {}
    previous_catalog_hash = None
    if output_path.is_file() and not args.no_resume:
        previous = json.loads(output_path.read_text(encoding="utf-8"))
        records = previous.get("scores", [])
        if previous.get("schema") == "science_skill_critic_scores_v1":
            records = [finalize_record(record) for record in records]
        existing = {record["id"]: record for record in records}
        previous_catalog_hash = previous.get("catalog_sha256")
    pending = [
        skill
        for skill in selected
        if not record_is_current(
            skill,
            existing.get(skill["id"]),
            model=args.model,
            source_root=source_root,
            catalog_unchanged=previous_catalog_hash == catalog_hash,
        )
    ]

    validator = load_validator(critic_root)
    client = ArkChatClient(
        api_key,
        model=args.model,
        base_url=args.base_url,
        timeout=args.timeout,
        retries=max(0, args.retries),
    )
    failures = []

    def checkpoint() -> None:
        ordered = [existing[skill["id"]] for skill in catalog["skills"] if skill["id"] in existing]
        payload = {
            "schema": SCHEMA,
            "catalog_sha256": catalog_hash,
            "model": args.model,
            "rubric_version": RUBRIC_VERSION,
            "finalization_version": "critic-evidence-contract-v2",
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "score_count": len(ordered),
            "scores": ordered,
            "failures": failures,
        }
        atomic_write_json(output_path, payload)

    completed_since_checkpoint = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        jobs = {
            pool.submit(
                score_one,
                skill,
                source_root=source_root,
                validator=validator,
                client=client,
            ): skill["id"]
            for skill in pending
        }
        for future in concurrent.futures.as_completed(jobs):
            skill_id = jobs[future]
            try:
                existing[skill_id] = future.result()
                print(f"scored {skill_id}", flush=True)
            except Exception as exc:  # keep the batch resumable
                failures.append({"id": skill_id, "error": f"{type(exc).__name__}: {exc}"})
                print(f"failed {skill_id}: {type(exc).__name__}", file=sys.stderr, flush=True)
            completed_since_checkpoint += 1
            if completed_since_checkpoint >= max(1, args.checkpoint_every):
                checkpoint()
                completed_since_checkpoint = 0

    checkpoint()
    selected_scored = sum(skill["id"] in existing for skill in selected)
    print(
        f"scorecard: {output_path} "
        f"({len(existing)} total; {selected_scored}/{len(selected)} selected scored)"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
