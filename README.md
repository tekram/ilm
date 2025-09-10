## Transcript Summarizer → GitHub Pages

This project processes transcripts (from Zoom cloud recordings or local files), summarizes them with an LLM (OpenAI, Gemini, or local Ollama), and generates static HTML pages in `docs/` for GitHub Pages.

### What it does
- **Zoom Mode**: Fetches Zoom cloud recording transcripts via Server-to-Server OAuth
  - Prefers AI Companion summaries when available, falls back to transcripts
- **Local Mode**: Processes transcript files from a local directory
  - Supports .txt, .vtt, .srt, and .transcript files
- Summarizes each transcript using an LLM
- Creates one HTML page per meeting/transcript summary in `docs/meetings/`
- Rebuilds `docs/index.html` with links to all summaries
- Tracks processed files to avoid reprocessing

### Prerequisites
- Python 3.10+
- A Zoom Server-to-Server OAuth app with these scopes:
  - `recording:read:admin` (or `recording:read` for a single user)
- An LLM: OpenAI, Gemini, or a local Ollama model running

### Setup
1. Create a Zoom Server-to-Server OAuth app
   - App Marketplace → Build App → Server-to-Server OAuth
   - Note your `Account ID`, `Client ID`, and `Client Secret`
   - Add scope `recording:read:admin`

2. Configure environment variables
   - Create a `.env` file in the repo root and fill in values:

```bash
# Zoom (Server-to-Server OAuth)
ZOOM_ACCOUNT_ID=...
ZOOM_CLIENT_ID=...
ZOOM_CLIENT_SECRET=...
# Optional: limit recordings to a specific host
# ZOOM_HOST_EMAIL=host@example.com

# Choose one provider
LLM_PROVIDER=openai  # or gemini or ollama

# OpenAI
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini

# Gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-1.5-pro

# Ollama (local; no API key)
OLLAMA_MODEL=llama3.1:8b
# Optional if not default
# OLLAMA_HOST=http://localhost:11434

```

3. Install dependencies (Windows PowerShell)

```powershell
python -m venv .venv
\.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

4. Run the pipeline

**For Zoom recordings:**
```powershell
python -m src.main --days 7
```

**For local transcript files:**
```powershell
python -m src.main --local-dir "C:\path\to\transcripts"
```

This will:
- **Zoom mode**: Fetch recordings for the last 7 days, extract transcripts (VTT → plain text) or use AI Companion SUMMARY if available
- **Local mode**: Process all supported transcript files (.txt, .vtt, .srt, .transcript) from the specified directory
- Summarize with the selected LLM
- Write pages into `docs/meetings/` and rebuild `docs/index.html`
- Skip already-processed files using the manifest and stable page IDs

### Filtering meetings by topic
Filter to specific meeting titles using CLI arguments:
- Exact match (default): `--topics "Team Weekly Sync" --topics "Product Council"`
- Contains match: add `--match contains` to allow partial topic matches

### Date ranges
- Default: last 7 days (`--days 7`)
- Custom range: `--from 2024-01-01 --to 2024-01-31`
- Specific days back: `--days 30`

### GitHub Pages
GitHub Pages can serve directly from the `docs/` folder on your default branch.
- Commit and push with GitHub Desktop
- In your repository → Settings → Pages → Build and deployment:
  - Source: Deploy from a branch
  - Branch: `main` (or your default), Folder: `/docs`
- Your site will be available at `https://<your-username>.github.io/<repo-name>/`

### Scheduling (optional)
To run automatically, add a GitHub Actions workflow that runs `python -m src.main` on a schedule and commits updated `docs/` back. Add `ZOOM_*`, `OPENAI_API_KEY` or `GEMINI_API_KEY` as Actions secrets depending on provider.

### Notes
- The script prefers AI Companion `SUMMARY` files when present; otherwise uses `TRANSCRIPT`/`VTT`/`TXT`.
- Large transcripts are chunked and summarized in parts, then merged.
- Providers:
  - OpenAI: set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, optional `OPENAI_MODEL`.
  - Gemini: set `LLM_PROVIDER=gemini`, `GEMINI_API_KEY`, optional `GEMINI_MODEL`.
  - Ollama: install and run Ollama locally, pull a model (e.g., `ollama pull llama3.1:8b`), set `LLM_PROVIDER=ollama` and `OLLAMA_MODEL`. Optionally set `OLLAMA_HOST`.

### Commands cheat sheet
```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# Zoom mode - Run with topics filter
python -m src.main --topics "Team Weekly Sync" --topics "Product Council"
# Run using partial matches
python -m src.main --topics "Weekly" --match contains

# Zoom mode - Custom date range
python -m src.main --from 2024-01-01 --to 2024-01-31

# Local mode - Process local transcript files
python -m src.main --local-dir "C:\transcripts"
# Local mode with topic filtering (based on filename)
python -m src.main --local-dir "C:\transcripts" --topics "Weekly" --match contains

# Clean summaries and rebuild (works for both modes)
Remove-Item -Recurse -Force docs\meetings\*
Remove-Item -Force docs\manifest.json
# Then run either:
python -m src.main --days 30  # Zoom mode
# OR:
python -m src.main --local-dir "C:\transcripts"  # Local mode
```

### Local File Processing

When using `--local-dir`, the script:
- Scans the directory for transcript files with extensions: `.txt`, `.vtt`, `.srt`, `.transcript`
- Converts VTT files to plain text automatically
- Generates meeting titles from filenames (removes common patterns, capitalizes)
- Uses file modification time as the meeting timestamp
- Creates stable IDs based on filename and timestamp to avoid reprocessing
- Supports the same topic filtering as Zoom mode (applied to generated titles)

**Example local file structure:**
```
C:\transcripts\
├── weekly-standup-2024-01-15.txt
├── product-review-meeting.vtt
├── team-retrospective.transcript
└── client-call-notes.txt
```


