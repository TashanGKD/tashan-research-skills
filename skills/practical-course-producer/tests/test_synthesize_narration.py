from __future__ import annotations

import importlib.util
import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "synthesize_narration.py"


def load_module():
    spec = importlib.util.spec_from_file_location("synthesize_narration", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load narration synthesizer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NarrationSynthesisTests(unittest.TestCase):
    def test_chinese_default_is_volcengine_with_edge_fallback(self) -> None:
        module = load_module()
        self.assertEqual(module.DEFAULT_PROVIDER, "volcengine")
        self.assertEqual(module.DEFAULT_FALLBACK_PROVIDER, "edge-tts")
        self.assertEqual(module.DEFAULT_VOLCENGINE_RESOURCE_ID, "seed-tts-2.0")
        self.assertEqual(module.DEFAULT_VOLCENGINE_SPEAKER, "zh_female_vv_uranus_bigtts")
        self.assertEqual(module.DEFAULT_VOICE, "zh-CN-XiaoxiaoNeural")
        self.assertEqual(module.DEFAULT_RATE, "+0%")
        self.assertEqual(
            module.VOLCENGINE_API_KEY_CONSOLE_URL,
            "https://console.volcengine.com/speech/new/setting/apikeys?projectName=default",
        )

    def test_missing_volcengine_key_points_to_api_key_console(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_value:
            audio = Path(temp_value) / "raw.mp3"
            with self.assertRaisesRegex(RuntimeError, "console.volcengine.com/speech/new/setting/apikeys"):
                module.volcengine_save(
                    "测试。",
                    audio,
                    api_key=None,
                    speaker=None,
                    resource_id=module.DEFAULT_VOLCENGINE_RESOURCE_ID,
                    endpoint=module.DEFAULT_VOLCENGINE_ENDPOINT,
                )

    def test_rejected_volcengine_key_points_to_console_without_leaking_key(self) -> None:
        module = load_module()
        error = module.HTTPError(
            module.DEFAULT_VOLCENGINE_ENDPOINT,
            401,
            "Unauthorized",
            {},
            io.BytesIO(b'{"message":"Invalid X-Api-Key: secret-key"}'),
        )
        with tempfile.TemporaryDirectory() as temp_value:
            audio = Path(temp_value) / "raw.mp3"
            with mock.patch.object(module, "urlopen", side_effect=error):
                with self.assertRaises(RuntimeError) as raised:
                    module.volcengine_save(
                        "测试。",
                        audio,
                        api_key="secret-key",
                        speaker=None,
                        resource_id=module.DEFAULT_VOLCENGINE_RESOURCE_ID,
                        endpoint=module.DEFAULT_VOLCENGINE_ENDPOINT,
                    )
        message = str(raised.exception)
        self.assertIn(module.VOLCENGINE_API_KEY_CONSOLE_URL, message)
        self.assertNotIn("secret-key", message)

    def test_markdown_is_reduced_to_spoken_text(self) -> None:
        module = load_module()
        source = "# 口播草稿\n\n先看 `contacts.csv`。\n\n**然后**检查[结果](https://example.com)。\n"
        self.assertEqual(module.spoken_text(source), "先看 contacts.csv。\n然后检查结果。")

    def test_sentence_boundaries_include_lead_in(self) -> None:
        module = load_module()
        metadata = [
            {"type": "SentenceBoundary", "offset": 1_000_000, "duration": 16_000_000, "text": "第一句。"},
            {"type": "SentenceBoundary", "offset": 16_500_000, "duration": 16_000_000, "text": "第二句。"},
        ]
        segments = module.timeline_segments(metadata, lead_in_ms=250)
        self.assertEqual(segments[0], {"text": "第一句。", "start": 0.35, "end": 1.9})
        self.assertEqual(segments[1], {"text": "第二句。", "start": 1.9, "end": 3.5})

    def test_volcengine_request_uses_official_v3_contract_and_subtitles(self) -> None:
        module = load_module()
        response_payloads = [
            {
                "code": 0,
                "data": base64.b64encode(b"mp3-").decode("ascii"),
                "sentence": {
                    "text": "先看文件。",
                    "words": [{"word": "先看文件。", "startTime": 0.1, "endTime": 0.9}],
                },
            },
            {
                "code": 0,
                "data": base64.b64encode(b"data").decode("ascii"),
                "sentence": {
                    "text": "再检查结果。",
                    "words": [{"word": "再检查结果。", "startTime": 0.9, "endTime": 1.8}],
                },
            },
            {"code": 20000000, "message": "OK", "data": None},
        ]

        class FakeResponse:
            headers = {"X-Tt-Logid": "log-id"}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return "".join(json.dumps(item) for item in response_payloads).encode("utf-8")

        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse()

        with tempfile.TemporaryDirectory() as temp_value:
            audio = Path(temp_value) / "raw.mp3"
            with mock.patch.object(module, "urlopen", side_effect=fake_urlopen):
                result = module.volcengine_save(
                    "先看文件。再检查结果。",
                    audio,
                    api_key="secret-key",
                    speaker="speaker-id",
                    resource_id="seed-tts-2.0",
                    endpoint=module.DEFAULT_VOLCENGINE_ENDPOINT,
                )

            request = captured["request"]
            body = json.loads(request.data.decode("utf-8"))
            headers = {key.lower(): value for key, value in request.header_items()}
            self.assertEqual(request.full_url, module.DEFAULT_VOLCENGINE_ENDPOINT)
            self.assertEqual(headers["x-api-key"], "secret-key")
            self.assertEqual(headers["x-api-resource-id"], "seed-tts-2.0")
            self.assertEqual(headers["x-api-app-key"], module.VOLCENGINE_APP_KEY)
            self.assertIn("x-api-request-id", headers)
            self.assertEqual(body["req_params"]["speaker"], "speaker-id")
            self.assertTrue(body["req_params"]["audio_params"]["enable_subtitle"])
            self.assertTrue(json.loads(body["req_params"]["additions"])["enable_timestamp"])
            self.assertEqual(audio.read_bytes(), b"mp3-data")
            self.assertEqual(result["segments"][1]["start"], 0.9)
            self.assertEqual(result["log_id"], "log-id")

    def test_volcengine_failure_uses_edge_and_records_fallback(self) -> None:
        module = load_module()

        async def fake_edge_save(_text, audio, metadata, *_args):
            audio.write_bytes(b"edge-audio")
            metadata.write_text(
                json.dumps(
                    {"type": "SentenceBoundary", "offset": 0, "duration": 10_000_000, "text": "回退。"}
                )
                + "\n",
                encoding="utf-8",
            )

        with tempfile.TemporaryDirectory() as temp_value:
            temp = Path(temp_value)
            with mock.patch.object(module, "volcengine_save", side_effect=RuntimeError("quota exhausted")), mock.patch.object(
                module, "edge_save", side_effect=fake_edge_save
            ):
                result = module.generate_raw_audio(
                    text="回退。",
                    raw_audio=temp / "raw.mp3",
                    raw_metadata=temp / "metadata.jsonl",
                    provider="volcengine",
                    fallback_provider="edge-tts",
                    api_key="secret-key",
                    speaker="speaker-id",
                    resource_id="seed-tts-2.0",
                    endpoint=module.DEFAULT_VOLCENGINE_ENDPOINT,
                    voice=module.DEFAULT_VOICE,
                    rate=module.DEFAULT_RATE,
                    volume="+0%",
                    pitch="+0Hz",
                    lead_in_ms=250,
                )

        self.assertEqual(result["provider"], "edge-tts")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["fallback_from"], "volcengine")
        self.assertIn("quota exhausted", result["fallback_reason"])
        self.assertNotIn("secret-key", json.dumps(result))

    def test_volcengine_failure_is_reported_when_fallback_is_disabled(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_value:
            temp = Path(temp_value)
            with mock.patch.object(module, "volcengine_save", side_effect=RuntimeError("authentication failed")):
                with self.assertRaisesRegex(RuntimeError, "Volcengine TTS failed"):
                    module.generate_raw_audio(
                        text="不回退。",
                        raw_audio=temp / "raw.mp3",
                        raw_metadata=temp / "metadata.jsonl",
                        provider="volcengine",
                        fallback_provider="none",
                        api_key="secret-key",
                        speaker="speaker-id",
                        resource_id="seed-tts-2.0",
                        endpoint=module.DEFAULT_VOLCENGINE_ENDPOINT,
                        voice=module.DEFAULT_VOICE,
                        rate=module.DEFAULT_RATE,
                        volume="+0%",
                        pitch="+0Hz",
                        lead_in_ms=250,
                    )


if __name__ == "__main__":
    unittest.main()
