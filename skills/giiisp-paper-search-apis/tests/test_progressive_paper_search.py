import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "progressive_paper_search.py"


def run_progressive(*args):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]


def test_dry_run_emits_start_request_and_complete_events_without_network():
    events = run_progressive("--query", "test query", "--mode", "arxiv-title", "--dry-run")

    assert [event["event"] for event in events] == [
        "search_started",
        "request_prepared",
        "search_complete",
    ]
    assert events[1]["request"]["url"] == "https://giiisp.com/first/paper/searchArxivByTitle"
    assert events[1]["request"]["body"] == {"key": "test query", "pageNum": 1, "pageSize": 10}
    assert events[-1]["dry_run"] is True


def test_expansion_plan_emits_each_expanded_route_and_page_in_order():
    events = run_progressive(
        "--query",
        "test query",
        "--mode",
        "arxiv-title",
        "--expand",
        "arxiv-abstract,oa",
        "--max-pages",
        "2",
        "--dry-run",
    )

    request_events = [event for event in events if event["event"] == "request_prepared"]
    assert [event["route"]["mode"] for event in request_events] == [
        "arxiv-title",
        "arxiv-title",
        "arxiv-abstract",
        "arxiv-abstract",
        "oa",
        "oa",
    ]
    assert [event["route"]["page_num"] for event in request_events] == [1, 2, 1, 2, 1, 2]
    assert events[-1]["planned_requests"] == 6
