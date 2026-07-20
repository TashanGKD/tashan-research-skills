import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "build_agentscope_trigger_decisions.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("build_agentscope_triggers", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_decisions_extracts_last_json_and_preserves_oracle(tmp_path):
    module = load_module()
    queries = {
        "trigger_queries": [
            {"query": "verify outputs", "should_trigger": True},
            {"query": "write prose", "should_trigger": False},
        ]
    }
    answer = {
        "decisions": [
            {"query": "verify outputs", "decision": "result-verification"},
            {"query": "write prose", "decision": "none"},
        ]
    }
    report = {
        "status": "pass",
        "final_text": "prompt with {example}\n" + json.dumps(answer),
    }

    decisions = module.build_decisions(report, queries, "result-verification")

    assert decisions == [
        {
            "query": "verify outputs",
            "should_trigger": True,
            "decisions": ["result-verification"],
        },
        {
            "query": "write prose",
            "should_trigger": False,
            "decisions": ["none"],
        },
    ]


def test_build_decisions_rejects_query_reordering():
    module = load_module()
    queries = {
        "trigger_queries": [
            {"query": "first", "should_trigger": True},
            {"query": "second", "should_trigger": False},
        ]
    }
    report = {
        "status": "pass",
        "final_text": json.dumps(
            {
                "decisions": [
                    {"query": "second", "decision": "none"},
                    {"query": "first", "decision": "result-verification"},
                ]
            }
        ),
    }

    with pytest.raises(ValueError, match="verbatim order"):
        module.build_decisions(report, queries, "result-verification")


def test_build_decisions_accepts_legacy_top_level_query_array():
    module = load_module()
    queries = [{"query": "write methods", "should_trigger": True}]
    report = {
        "status": "pass",
        "final_text": json.dumps(
            {
                "decisions": [
                    {
                        "query": "write methods",
                        "decision": "research-methods-writer",
                    }
                ]
            }
        ),
    }

    result = module.build_decisions(report, queries, "research-methods-writer")

    assert result[0]["decisions"] == ["research-methods-writer"]


def test_build_decisions_accepts_queries_key():
    module = load_module()
    queries = {"queries": [{"query": "build proof", "should_trigger": True}]}
    report = {
        "status": "pass",
        "final_text": json.dumps(
            {"decisions": [{"query": "build proof", "decision": "proof-writer"}]}
        ),
    }

    result = module.build_decisions(report, queries, "proof-writer")

    assert result[0]["should_trigger"] is True
