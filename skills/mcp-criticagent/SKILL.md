---
name: mcp-criticagent
description: Evaluate MCP (Model Context Protocol) servers and tools end to end — deploy from a GitHub URL or npm package, test protocol communication and tool calls, run AI-generated smart tests, and score repository sustainability and popularity. Use this skill whenever the user wants to test, evaluate, audit, score, or vet an MCP server, MCP tool, or MCP package, or asks "does this MCP work" or "is this MCP any good", even if they only paste a GitHub URL or a package name.
---

# MCP-CriticAgent

You evaluate an MCP tool in three layers, each with its own verdict. Never
merge them into one number without showing the parts.

| Layer | Question it answers | How |
| --- | --- | --- |
| 1. Deploy + protocol | Does it start and speak MCP? | npm deployment, `tools/list`, first tool call |
| 2. Behavior | Do its tools actually work? | AI smart tests (generated test cases, executed and verified) |
| 3. Repository health | Will it still work next quarter? | GitHub sustainability + popularity scoring |

## Prerequisites

Run from the repository root (contains `src/` and `pyproject.toml`).

- Python deps: `uv sync` (or `pip install -e .`)
- Node.js 18+ with `npx` (MCP tools are deployed as npm packages)
- Optional env in `.env`: `DASHSCOPE_API_KEY` for layer 2 smart tests
  (apply at `https://help.aliyun.com/zh/model-studio/get-api-key`).
  `HUB_TOKEN` (GitHub) is not required: layer 3 scoring works without it
  and only risks rate-limiting on heavy use. Supabase keys only if the
  user wants results exported.

Check what is available before promising layers: without a model key, layer 2
falls back to basic protocol tests; without `HUB_TOKEN`, layer 3 may be
rate-limited.

## Workflow

1. **Identify the target.** A GitHub URL goes to `test-url`; a bare npm
   package name (e.g. `@upstash/context7-mcp`) goes to `test-package`. If the
   user is exploring, `list-tools --search <term>` queries the built-in
   database of 5000+ known MCP tools.

2. **Pick the flags for the situation** (defaults enable everything):

```bash
# Full evaluation (all three layers, report saved):
uv run python -m src.main test-url "https://github.com/OWNER/REPO" --no-db-export

# Quick connectivity check only (fast, no model key needed):
uv run python -m src.main test-package "<package>" --no-smart --no-evaluate --no-db-export

# Add --verbose when the user wants to see what the tool calls returned.
```

Keep `--no-db-export` unless the user explicitly wants Supabase export.
Deployment can take minutes for heavy packages; the default timeout is 600s.

3. **Read the results.** Reports land in `data/test_results/` (JSON + HTML).
   Interpret for the user:
   - Layer 1: deployment success, protocol handshake, number of tools
     discovered, first-tool-call result. A tool that deploys but fails every
     call is broken regardless of its stars.
   - Layer 2: smart-test success rate (threshold 0.7). Quote failing test
     cases with their error messages as evidence.
   - Layer 3: `final_score` (0-100) = sustainability 50% (recency, commit
     frequency, stability, issue responsiveness/health) + popularity 50%
     (stars 70%, forks 30%). A high score with layer-1 failures means a
     popular repo whose current release is broken — say exactly that.

4. **Report** three layer verdicts with evidence, then a recommendation:
   use / use with caution / avoid. State which layers were skipped and why
   (missing key, timeout) rather than presenting a partial run as complete.

## Caveats

- Deployment executes third-party npm packages: prefer running in a sandbox
  or container when the package is untrusted; never expose user secrets in
  the environment beyond the keys the run needs.
- The tool database (`data/mcp.csv`) is a snapshot; a missing entry means
  unknown, not bad. Use `test-url` for anything not in it.
- Layer 3 scores the repository, not the code quality of the MCP protocol
  implementation — layers 1-2 are the ground truth for "does it work".
