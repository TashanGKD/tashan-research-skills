import importlib.util
import json
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "adapt_host_tool_assertions.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("adapt_host_tool_assertions", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_adapt_copy_changes_only_declared_tool_names(tmp_path):
    module = load_module()
    source = tmp_path / "source"
    target = tmp_path / "target"
    (source / "evals").mkdir(parents=True)
    (source / "SKILL.md").write_text("# Example\n", encoding="utf-8")
    payload = {
        "evals": [
            {
                "id": "case-1",
                "prompt": "Do the work",
                "assertions": ["done"],
                "tool_assertions": [
                    {"type": "tool-called", "name": "shell_command"},
                    {"type": "tool-not-called", "name": "browser"},
                ],
            }
        ]
    }
    (source / "evals" / "evals.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    manifest = module.adapt_skill(source, target, {"shell_command": "Write"})

    adapted = json.loads((target / "evals" / "evals.json").read_text(encoding="utf-8"))
    assertions = adapted["evals"][0]["tool_assertions"]
    assert assertions[0]["name"] == "Write"
    assert assertions[1]["name"] == "browser"
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "# Example\n"
    assert manifest["changed_assertions"] == [
        {
            "case_id": "case-1",
            "assertion_index": 0,
            "from": "shell_command",
            "to": "Write",
        }
    ]
    assert manifest["source_tree_sha256"] != manifest["adapted_tree_sha256"]
    assert json.loads((target / "host-tool-adaptation.json").read_text(encoding="utf-8")) == manifest


def test_adapt_requires_a_used_mapping_and_new_target(tmp_path):
    module = load_module()
    source = tmp_path / "source"
    (source / "evals").mkdir(parents=True)
    (source / "evals" / "evals.json").write_text(
        json.dumps({"evals": [{"id": "case", "tool_assertions": []}]}),
        encoding="utf-8",
    )

    try:
        module.adapt_skill(source, tmp_path / "unused", {"shell_command": "Write"})
    except ValueError as exc:
        assert "did not match" in str(exc)
    else:
        raise AssertionError("unused mappings must fail")

    target = tmp_path / "existing"
    target.mkdir()
    try:
        module.adapt_skill(source, target, {})
    except FileExistsError:
        pass
    else:
        raise AssertionError("existing targets must not be overwritten")
