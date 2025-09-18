## Transcript Summarizer → GitHub Pages

This project processes transcripts (from Zoom cloud recordings or local files), summarizes them with an LLM (OpenAI, Gemini, or local Ollama), and generates static HTML pages in `docs/` for GitHub Pages.

### What it does
- **Multi-Meeting Type Support**: Organizes different types of meetings (e.g., Tuhfa Al-Muhtaaj, Manthoma) with separate indexes
- **Zoom Mode**: Fetches Zoom cloud recording transcripts via Server-to-Server OAuth
  - Prefers AI Companion summaries when available, falls back to transcripts
- **Local Mode**: Processes transcript files from organized local directories
  - Supports .txt, .vtt, .srt, and .transcript files
- Summarizes each transcript using an LLM (OpenAI GPT-4o-mini by default)
- Creates organized HTML pages with navigation between meeting types
- Rebuilds main index and type-specific indexes
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

**For all meeting types (recommended):**
```powershell
python -m src.main --all-types
```

**For specific meeting type:**
```powershell
python -m src.main --meeting-type tuhfa-al-muhtaaj
python -m src.main --meeting-type manthoma
```

**Legacy modes (still supported):**
```powershell
# Zoom recordings
python -m src.main --days 7

# Local transcript files
python -m src.main --local-dir "C:\path\to\transcripts"
```

This will:
- **Multi-type mode**: Process organized transcript files from `recordings/[meeting-type]/` directories
- **Zoom mode**: Fetch recordings for the last 7 days, extract transcripts (VTT → plain text) or use AI Companion SUMMARY if available
- **Local mode**: Process all supported transcript files (.txt, .vtt, .srt, .transcript) from the specified directory
- Summarize with OpenAI GPT-4o-mini (hardcoded API key)
- Write organized pages with separate indexes for each meeting type
- Skip already-processed files using the enhanced manifest

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

# Multi-type mode (recommended)
python -m src.main --all-types                    # Process all meeting types
python -m src.main --meeting-type tuhfa-al-muhtaaj # Process only Tuhfa Al-Muhtaaj
python -m src.main --meeting-type manthoma         # Process only Manthoma

# Multi-type mode with topic filtering
python -m src.main --all-types --topics "Partnership" --match contains

# Legacy Zoom mode - Run with topics filter
python -m src.main --topics "Team Weekly Sync" --topics "Product Council"
# Legacy Zoom mode - Custom date range
python -m src.main --from 2024-01-01 --to 2024-01-31

# Legacy local mode - Process local transcript files
python -m src.main --local-dir "C:\transcripts"

# Clean summaries and rebuild
Remove-Item -Recurse -Force docs\tuhfa-al-muhtaaj\meetings\*
Remove-Item -Recurse -Force docs\manthoma\meetings\*
Remove-Item -Force docs\manifest.json
python -m src.main --all-types  # Rebuild everything
```

### Multi-Type File Processing

The system now organizes transcript files by meeting type:

**Current structure:**
```
recordings/
├── tuhfa-al-muhtaaj/     # Islamic jurisprudence lessons
│   ├── GMT20250529-170107_Recording.transcript.vtt
│   ├── GMT20250612-170429_Recording.transcript.vtt
│   └── ...
└── manthoma/             # Manthoma lessons  
    ├── GMT20241217-165921_Recording.transcript.vtt
    └── ...

docs/
├── index.html            # Main landing page
├── tuhfa-al-muhtaaj/
│   ├── index.html        # Tuhfa Al-Muhtaaj sessions
│   └── meetings/         # Individual session pages
└── manthoma/
    ├── index.html        # Manthoma sessions
    └── meetings/         # Individual session pages
```

**Processing behavior:**
- Scans each meeting type directory for transcript files: `.txt`, `.vtt`, `.srt`, `.transcript`
- Converts VTT files to plain text automatically
- Generates meeting titles from filenames and LLM analysis
- Uses file modification time as the meeting timestamp
- Creates stable IDs with meeting type prefix to avoid reprocessing
- Supports topic filtering across all meeting types


