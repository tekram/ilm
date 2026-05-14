# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Python CLI that converts meeting transcripts (Zoom or local files) into a static HTML site published via GitHub Pages. Transcripts are summarized using OpenAI, Gemini, or Ollama. Targets Islamic lesson recordings organized by meeting type.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Requires `.env` file in root with credentials (see README for full template). Key vars: `LLM_PROVIDER`, `OPENAI_API_KEY` (or Gemini/Ollama equivalents), Zoom OAuth creds if using Zoom mode.

## Running

```powershell
# Process all meeting types (primary workflow)
python -m src.main --all-types

# Single meeting type
python -m src.main --meeting-type tuhfa-al-muhtaaj

# Topic filter
python -m src.main --all-types --topics "Partnership" --match contains

# Full clean rebuild
Remove-Item -Recurse -Force docs\tuhfa-al-muhtaaj\meetings\*, docs\manthoma\meetings\*, docs\majma-al-fatawa-bilhind\meetings\*
Remove-Item -Force docs\manifest.json
python -m src.main --all-types
```

No test suite (test file is empty).

## Architecture

**Data flow:** CLI args + `.env` → `config.py` → input client → `llm.py` → `sitegen.py` → `docs/`

**`src/` modules:**
- `main.py` — CLI entry point, orchestrates the pipeline
- `config.py` — loads all env vars, defines meeting type configs
- `llm.py` — LLM provider abstraction; chunks large transcripts (8000 char limit), calls OpenAI/Gemini/Ollama
- `sitegen.py` — renders Jinja2 templates to HTML, manages `docs/manifest.json`
- `local_client.py` — scans `recordings/[meeting-type]/` for `.txt/.vtt/.srt/.transcript` files, parses dates/topics from filenames, converts VTT to plain text
- `zoom_client.py` / `zoom_extract.py` — Zoom Server-to-Server OAuth, downloads transcripts, prefers AI Companion SUMMARY over raw transcript

**Key directories:**
- `recordings/[meeting-type]/` — input transcript files (local mode)
- `docs/[meeting-type]/meetings/` — generated HTML per session
- `docs/manifest.json` — tracks processed file IDs to skip reprocessing
- `templates/` — Jinja2 `.html.j2` templates for main index, per-type index, individual meeting pages

**Meeting types** are defined in config and map to subdirectories in both `recordings/` and `docs/`. Adding a new meeting type requires updating config and creating the directory pair.

**Day-of-week rule for assigning meeting type** (derive the day from the date in the filename, e.g. `GMT20260512` → 2026-05-12):
- **Tuesday** → `majma-al-fatawa-bilhind`
- **Thursday** → `tuhfa-al-muhtaaj`
- If the day does not match either, check the existing `recordings/` subfolders or ask the user.

**Manifest deduplication:** Each processed file gets a stable ID (meeting-type prefix + filename). Already-processed IDs are skipped on subsequent runs. Delete manifest entries or the manifest file to force reprocessing.
