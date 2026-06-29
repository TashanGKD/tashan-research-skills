# PaperCheck Runtime Notes

## Architecture

- `scripts/extract_citation_evidence.py` is the default no-key path. It extracts citation/reference/context evidence from `.docx`.
- The mounted Codex model reviews the extracted evidence and writes the semantic citation-support judgment.
- `assets/paperchecker-rules` is the bundled TaShan-PaperChecker rules engine for GB/T 7714-2015, UCAS-style format checks, and citation/reference matching.

The old PaperCheck AI project needed a provider API key because it was not itself a Codex skill. This skill does not need that pattern: it uses local extraction plus the current model that is already running the skill.

## Evidence Extraction

```powershell
python ..\scripts\extract_citation_evidence.py "<path-to-paper.docx>" --out "<path-to-evidence.json>"
```

The JSON contains:

- citation markers and expanded ranges
- numbered references
- missing citations and unused references
- local context around each citation
- `needs_model_review` markers for citations where Codex should judge support

Review rule: judge only from extracted context, reference entry, and any user-supplied paper/PDF. If the actual cited paper content is unavailable, mark that limitation instead of overclaiming.

## Rules Engine

Bundled source: `assets/paperchecker-rules`

Install:

```powershell
cd .\assets\paperchecker-rules
pip install -r requirements.txt
```

Start:

```powershell
python run_server.py
```

Default local URL after startup is usually `http://127.0.0.1:8002`. Confirm with:

```powershell
Invoke-RestMethod http://127.0.0.1:8002/api/health
```

Upload check:

```powershell
curl.exe -s -X POST -F "file=@<path-to-paper.docx>" -F "author_format=full" -F "citation_standard=ucas" "http://127.0.0.1:8002/api/v2/analysis/report" -o report.json
```

Expected success fields: `contract_version`, `run.status=succeeded`, `summary.match_rate`, and issue groups under `issues`.

## Known Limits

- Evidence extraction only supports `.docx` directly.
- Rules-service upload supports `.docx`, `.doc`, and `.pdf` according to the upstream rules project, but extraction quality depends on document structure.
- The current model can judge support from extracted context and reference text, but it cannot verify the actual cited paper's full content unless the paper/PDF is provided.

## Packaging Boundary

The skill package should contain `SKILL.md`, `agents/`, `scripts/`, `references/`, and cleaned `assets/paperchecker-rules`. It must not contain:

- provider API keys
- `node_modules`
- uploaded or sample papers
- generated markdown/JSON reports
- cache directories
- local config values
