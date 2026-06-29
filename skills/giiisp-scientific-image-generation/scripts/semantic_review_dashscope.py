import argparse
import base64
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DEFAULT_MODEL = "qwen3.7-plus"


def read_json(path):
    if not path:
        return None
    path = Path(path)
    if not path.exists() or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def infer_mime(path):
    suffix = Path(path).suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "application/octet-stream"


def image_data_url(path):
    path = Path(path)
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{infer_mime(path)};base64,{encoded}"


def extract_json_text(value):
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return json.loads(text)
    if isinstance(value, list):
        joined = []
        for item in value:
            if isinstance(item, dict):
                if item.get("type") == "text" and item.get("text"):
                    joined.append(item["text"])
                elif item.get("content"):
                    joined.append(str(item["content"]))
            else:
                joined.append(str(item))
        return extract_json_text("\n".join(joined))
    raise ValueError("response content is not parseable JSON text")


def first_choice_content(response_json):
    choices = response_json.get("choices") or []
    if not choices:
        raise ValueError("DashScope response did not include choices")
    message = choices[0].get("message") or {}
    return message.get("content")


def build_review_prompt(figure_spec, check, manifest):
    compact_manifest = {}
    if isinstance(manifest, dict):
        compact_manifest = {
            "run_id": manifest.get("run_id"),
            "status": manifest.get("status"),
            "task": manifest.get("task"),
            "output": manifest.get("output"),
        }
    return (
        "你是科研配图审查员。请只根据图片和下面的结构化要求审查，不要猜测未显示内容。\n"
        "输出必须是严格 JSON，不要 Markdown，不要解释性前后缀。JSON schema:\n"
        "{"
        "\"schema\":\"giiisp_semantic_review_v1\","
        "\"overall_ready_to_ship\":true|false,"
        "\"quality_review_axes\":[{\"name\":\"content_accuracy|layout_quality|text_readability|aesthetic_quality|artifact_severity\",\"status\":\"PASS|FAIL|UNCERTAIN\",\"score\":0-10,\"rationale\":\"...\"}],"
        "\"observed_labels\":[\"...\"],"
        "\"missing_required_labels\":[\"...\"],"
        "\"forbidden_labels_seen\":[\"...\"],"
        "\"issues\":[\"...\"],"
        "\"recommended_next_action\":\"deliver|edit|regenerate|manual_review\","
        "\"next_edit_prompt\":\"...\""
        "}\n\n"
        "figure_spec:\n"
        + json.dumps(figure_spec or {}, ensure_ascii=False, indent=2)
        + "\n\nmachine_check:\n"
        + json.dumps(check or {}, ensure_ascii=False, indent=2)
        + "\n\nmanifest_summary:\n"
        + json.dumps(compact_manifest, ensure_ascii=False, indent=2)
    )


def call_dashscope(model, api_key, image_path, prompt, timeout):
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url(image_path)}},
                ],
            }
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    request = Request(
        ENDPOINT,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            return {"status_code": response.status, "json": json.loads(text), "text": text}
    except HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"raw_text": text}
        return {"status_code": exc.code, "json": data, "text": text}
    except URLError as exc:
        return {"status_code": None, "json": {"error": str(exc)}, "text": str(exc)}


def blocked(reason, details=None):
    return {
        "schema": "giiisp_semantic_review_v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "provider": "dashscope",
        "status": "blocked",
        "blocker": {"reason": reason, "details": details or {}},
        "overall_ready_to_ship": None,
    }


def main():
    parser = argparse.ArgumentParser(description="Review a generated scientific image with DashScope Qwen vision models.")
    parser.add_argument("--image", help="Generated image path.")
    parser.add_argument("--run-dir", help="Run directory containing generated_image.*, figure_spec.json, check.json, and figure_manifest.json.")
    parser.add_argument("--figure-spec", help="Optional figure_spec.json path.")
    parser.add_argument("--check", help="Optional check.json path.")
    parser.add_argument("--manifest", help="Optional figure_manifest.json path.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="DashScope model, default qwen3.7-plus.")
    parser.add_argument("--out", help="Output semantic_review.json path.")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    run_dir = Path(args.run_dir) if args.run_dir else None
    image_path = Path(args.image) if args.image else None
    if not image_path and run_dir:
        for name in ["generated_image.png", "generated_image.jpg", "generated_image.jpeg", "generated_image.webp"]:
            candidate = run_dir / name
            if candidate.exists():
                image_path = candidate
                break
    out_path = Path(args.out) if args.out else (run_dir / "semantic_review.json" if run_dir else None)

    if not image_path or not image_path.exists():
        review = blocked("image file is missing", {"image": str(image_path) if image_path else None})
        if out_path:
            write_json(out_path, review)
        print(json.dumps(review, ensure_ascii=False, indent=2))
        return 2

    api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        review = blocked("missing DASHSCOPE_API_KEY")
        if out_path:
            write_json(out_path, review)
        print(json.dumps(review, ensure_ascii=False, indent=2))
        return 2

    figure_spec_path = Path(args.figure_spec) if args.figure_spec else (run_dir / "figure_spec.json" if run_dir else None)
    check_path = Path(args.check) if args.check else (run_dir / "check.json" if run_dir else None)
    manifest_path = Path(args.manifest) if args.manifest else (run_dir / "figure_manifest.json" if run_dir else None)
    figure_spec = read_json(figure_spec_path)
    check = read_json(check_path)
    manifest = read_json(manifest_path)
    prompt = build_review_prompt(figure_spec, check, manifest)
    response = call_dashscope(args.model, api_key, image_path, prompt, args.timeout)

    review = {
        "schema": "giiisp_semantic_review_v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "provider": "dashscope",
        "endpoint": ENDPOINT,
        "model": args.model,
        "status": "completed" if response.get("status_code") and 200 <= response["status_code"] < 300 else "blocked",
        "image_path": str(image_path),
        "figure_spec_path": str(figure_spec_path) if figure_spec_path else None,
        "check_path": str(check_path) if check_path else None,
        "manifest_path": str(manifest_path) if manifest_path else None,
        "dashscope_status_code": response.get("status_code"),
        "token_policy": "read from DASHSCOPE_API_KEY environment variable; token is not written to files",
    }

    if review["status"] == "completed":
        try:
            parsed = extract_json_text(first_choice_content(response["json"]))
            review.update(parsed)
            review["status"] = "completed"
        except Exception as exc:
            review["status"] = "blocked"
            review["blocker"] = {"reason": "failed to parse DashScope JSON review", "details": {"error": str(exc)}}
            review["raw_response_excerpt"] = response.get("text", "")[:1000]
    else:
        review["blocker"] = {
            "reason": "DashScope request failed",
            "details": {
                "status_code": response.get("status_code"),
                "response": response.get("json"),
            },
        }

    if out_path:
        write_json(out_path, review)
    print(json.dumps(review, ensure_ascii=False, indent=2))
    return 0 if review.get("status") == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
