"""
Rebuild only the index pages (main + per-type) using the new templates + existing manifest.
Does NOT process any transcripts or call the LLM.
"""
import os
import json
import sys

sys.path.insert(0, os.path.dirname(__file__))

from src.config import load_config
from src.sitegen import SiteGenerator, MeetingPage


def main():
    cfg = load_config()

    site = SiteGenerator(
        templates_dir=cfg.templates_dir,
        docs_dir=cfg.docs_dir,
        meeting_types=cfg.meeting_types,
    )

    # Load all pages from manifest
    manifest_path = os.path.join(cfg.docs_dir, "manifest.json")
    pages = []
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
        for entry in data:
            pages.append(MeetingPage(**entry))
        print(f"Loaded {len(pages)} pages from manifest.")
    else:
        print("No manifest found — indexes will be empty.")

    # Sort newest first
    pages.sort(key=lambda p: p.start_time, reverse=True)

    # Rebuild main index
    site.build_index(pages)
    print("Built main index: docs/index.html")

    # Rebuild per-type indexes
    site.build_type_indexes(pages)
    for mt in cfg.meeting_types:
        print(f"Built type index: docs/{mt}/index.html")

    print("Done.")


if __name__ == "__main__":
    main()
