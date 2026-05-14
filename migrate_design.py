"""
One-time script: rewrite existing meeting HTML files with the new Notion-inspired design.
Extracts title, start_time, and summary content from old files, then re-renders with new CSS.
"""
import os
import re
import glob

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")

NEW_TEMPLATE = '''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="color-scheme" content="light" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
    <style>
      *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
      html {{ background: #fafaf9; color: #37352f; color-scheme: light; }}
      body {{
        font-family: Inter, -apple-system, system-ui, 'Segoe UI', Helvetica, sans-serif;
        font-size: 16px;
        line-height: 1.55;
        color: #37352f;
        background: #fafaf9;
      }}

      /* ── Site Header ── */
      .site-header {{
        background: #0a1530;
        padding: 0 32px;
        height: 56px;
        display: flex;
        align-items: center;
        gap: 8px;
      }}
      .site-header a {{
        color: #a4a0c8;
        text-decoration: none;
        font-size: 14px;
        font-weight: 500;
        transition: color 0.12s;
      }}
      .site-header a:hover {{ color: #ffffff; }}
      .site-header .sep {{ color: #3a4a72; font-size: 14px; }}
      .site-header .current {{
        color: #d0ccf0;
        font-size: 14px;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 320px;
      }}

      /* ── Page Header ── */
      .page-header {{
        background: #0a1530;
        padding: 36px 32px 48px;
        border-bottom: 1px solid #1a2a52;
      }}
      .page-header-inner {{
        max-width: 760px;
        margin: 0 auto;
      }}
      .page-header h1 {{
        font-size: clamp(22px, 3.5vw, 32px);
        font-weight: 600;
        line-height: 1.2;
        letter-spacing: -0.5px;
        color: #ffffff;
        margin-bottom: 12px;
      }}
      .session-meta {{
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
      }}
      .meta-chip {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 12px;
        font-weight: 500;
        color: #a4a0c8;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 9999px;
        padding: 3px 10px;
      }}

      /* ── Content ── */
      .content-wrapper {{
        max-width: 760px;
        margin: 0 auto;
        padding: 48px 32px 80px;
      }}

      /* Markdown content typography */
      .summary-content {{
        font-size: 16px;
        line-height: 1.7;
        color: #37352f;
      }}
      .summary-content h1 {{
        font-size: 26px;
        font-weight: 600;
        letter-spacing: -0.3px;
        color: #1a1a1a;
        margin-top: 2.2em;
        margin-bottom: 0.7em;
        padding-bottom: 0.3em;
        border-bottom: 2px solid #e5e3df;
      }}
      .summary-content h2 {{
        font-size: 21px;
        font-weight: 600;
        letter-spacing: -0.2px;
        color: #1a1a1a;
        margin-top: 2em;
        margin-bottom: 0.6em;
        padding-bottom: 0.25em;
        border-bottom: 1px solid #e5e3df;
      }}
      .summary-content h3 {{
        font-size: 18px;
        font-weight: 600;
        color: #1a1a1a;
        margin-top: 1.6em;
        margin-bottom: 0.5em;
      }}
      .summary-content h4 {{
        font-size: 15px;
        font-weight: 600;
        color: #5d5b54;
        margin-top: 1.4em;
        margin-bottom: 0.4em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }}
      .summary-content p {{ margin: 1em 0; }}
      .summary-content ul,
      .summary-content ol {{
        margin: 1em 0;
        padding-left: 1.8em;
      }}
      .summary-content li {{ margin: 0.45em 0; }}
      .summary-content strong {{ font-weight: 600; color: #1a1a1a; }}
      .summary-content em {{ color: #5d5b54; }}
      .summary-content blockquote {{
        border-left: 3px solid #5645d4;
        padding: 0.6em 0 0.6em 1.2em;
        margin: 1.2em 0;
        color: #5d5b54;
        background: #f4f0fc;
        border-radius: 0 8px 8px 0;
      }}
      .summary-content hr {{
        border: none;
        border-top: 2px solid #e5e3df;
        margin: 2.5em 0;
      }}
      .summary-content code {{
        background: #f0eeec;
        padding: 0.1em 0.35em;
        border-radius: 4px;
        font-size: 0.9em;
        font-family: ui-monospace, 'SF Mono', Menlo, monospace;
      }}
      .summary-content pre {{
        background: #f0eeec;
        padding: 1.2em;
        border-radius: 8px;
        overflow-x: auto;
        margin: 1.2em 0;
      }}
      .summary-content pre code {{ background: none; padding: 0; }}
      .summary-content > h1:first-child,
      .summary-content > h2:first-child,
      .summary-content > h3:first-child {{ margin-top: 0; }}

      /* ── Footer ── */
      footer {{
        border-top: 1px solid #e5e3df;
        padding: 28px 32px;
        text-align: center;
        font-size: 13px;
        color: #a4a097;
      }}

      @media (max-width: 560px) {{
        .site-header, .page-header {{ padding-left: 20px; padding-right: 20px; }}
        .content-wrapper {{ padding-left: 20px; padding-right: 20px; }}
        .site-header .current {{ max-width: 160px; }}
      }}
    </style>
  </head>
  <body>

    <header class="site-header">
      <a href="../../../index.html">Islamic Learning Materials</a>
      <span class="sep">/</span>
      <a href="../../index.html">Sessions</a>
      <span class="sep">/</span>
      <span class="current">{title}</span>
    </header>

    <div class="page-header">
      <div class="page-header-inner">
        <h1>{title}</h1>
        <div class="session-meta">
          <span class="meta-chip">&#128197; {date}</span>
          {time_chip}
        </div>
      </div>
    </div>

    <div class="content-wrapper">
      <div class="summary-content">{content}</div>
    </div>

    <footer>
      <a href="../../index.html" style="color:#5645d4;text-decoration:none;font-weight:500;">&larr; Back to sessions</a>
    </footer>

  </body>
</html>
'''


def extract_text(html, tag_pattern):
    """Extract inner content of first matching tag."""
    m = re.search(tag_pattern, html, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def migrate_file(filepath):
    with open(filepath, encoding="utf-8") as f:
        old_html = f.read()

    # Extract title from <title> tag
    title = extract_text(old_html, r'<title>(.*?)</title>')
    # Strip "– Meeting Summary" suffix if present
    title = re.sub(r'\s*[–-]\s*Meeting Summary\s*$', '', title).strip()
    if not title:
        title = "Session"

    # Extract date from .meta div or header meta
    date_match = re.search(r'Start:\s*([\d\-T:.Z+]+)', old_html)
    start_time = date_match.group(1).strip() if date_match else ""
    date_str = start_time[:10] if start_time else ""
    time_str = start_time[11:16] if len(start_time) > 10 else ""
    time_chip = f'<span class="meta-chip">&#128336; {time_str}</span>' if time_str else ""

    # Extract summary-content div
    content = extract_text(old_html, r'<div class="summary-content">(.*?)</div>\s*</main>', )
    if not content:
        # Try a broader match
        content = extract_text(old_html, r'<div class="summary-content">(.*?)</div>')
    if not content:
        print(f"  WARNING: could not extract content from {filepath}")
        return False

    new_html = NEW_TEMPLATE.format(
        title=title,
        date=date_str,
        time_chip=time_chip,
        content=content,
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_html)
    return True


def main():
    meeting_types = ["tuhfa-al-muhtaaj", "manthoma", "majma-al-fatawa-bilhind"]
    total = 0
    for mt in meeting_types:
        meetings_dir = os.path.join(DOCS_DIR, mt, "meetings")
        if not os.path.isdir(meetings_dir):
            print(f"Skipping {mt} (no meetings dir)")
            continue
        files = glob.glob(os.path.join(meetings_dir, "*.html"))
        print(f"{mt}: {len(files)} files")
        for fp in sorted(files):
            ok = migrate_file(fp)
            status = "✓" if ok else "✗"
            print(f"  {status} {os.path.basename(fp)}")
            if ok:
                total += 1
    print(f"\nMigrated {total} meeting files.")


if __name__ == "__main__":
    main()
