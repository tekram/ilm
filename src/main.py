from __future__ import annotations

import argparse
import datetime as dt
import os
from datetime import datetime
from typing import List

from dateutil.relativedelta import relativedelta
from tqdm import tqdm

from .config import load_config
from .zoom_client import ZoomClient
from .local_client import LocalFileClient
from .llm import LlmSummarizer
from .sitegen import SiteGenerator, MeetingPage


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch Zoom transcripts, summarize via LLM, generate HTML in docs/.")
    p.add_argument("--days", type=int, default=7, help="Number of past days to fetch recordings for")
    p.add_argument("--from", dest="from_date", type=str, default=None, help="YYYY-MM-DD start date (overrides --days)")
    p.add_argument("--to", dest="to_date", type=str, default=None, help="YYYY-MM-DD end date (defaults today)")
    p.add_argument("--topics", type=str, action="append", help="Meeting topic(s). Repeat or separate by comma.")
    p.add_argument(
        "--match",
        type=str,
        default="exact",
        choices=["exact", "contains"],
        help="Topic match mode: exact (default) or contains",
    )
    p.add_argument("--local-dir", type=str, default=None, help="Process local transcript files from this directory instead of fetching from Zoom")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config()

    # Determine processing mode
    local_mode = args.local_dir is not None
    
    if local_mode:
        # Validate local directory
        local_dir = args.local_dir
        if not os.path.exists(local_dir):
            raise SystemExit(f"Local directory does not exist: {local_dir}")
    else:
        # Validate Zoom credentials
        if not cfg.zoom.access_token:
            raise SystemExit("Missing Zoom access token in environment (ZOOM_ACCESS_TOKEN).")

    # Validate LLM provider config
    if cfg.llm.provider == "openai" and not cfg.llm.openai_api_key:
        raise SystemExit("Missing OPENAI_API_KEY.")
    if cfg.llm.provider == "gemini" and not cfg.llm.gemini_api_key:
        raise SystemExit("Missing GEMINI_API_KEY.")

    # Initialize clients
    site = SiteGenerator(cfg.templates_dir, cfg.docs_dir, cfg.meetings_dir)
    summarizer = LlmSummarizer.from_config(cfg.llm)

    # Load existing pages to avoid reprocessing
    pages: List[MeetingPage] = site.load_manifest()
    existing_ids = {p.id for p in pages}

    # Topic filtering from CLI
    topics: List[str] = []
    if args.topics:
        for t in args.topics:
            topics.extend([s.strip() for s in t.split(",") if s.strip()])

    def topic_matches(candidate: str) -> bool:
        if not topics:
            return True
        c = (candidate or "").strip().lower()
        if args.match == "contains":
            return any(t.lower() in c for t in topics)
        return any(c == t.lower() for t in topics)

    if local_mode:
        # Process local files
        local_client = LocalFileClient(local_dir)
        transcript_files = local_client.list_transcript_files()
        
        local_meetings = []
        for tf in transcript_files:
            meeting = local_client.create_meeting_from_file(tf)
            if meeting:
                local_meetings.append(meeting)
        
        # Apply topic filtering
        if topics:
            local_meetings = [m for m in local_meetings if topic_matches(m.topic)]
        
        # Process each local meeting
        for meeting in tqdm(local_meetings, desc="Processing local files"):
            page_id = meeting.meeting_id
            filename = f"meetings/{page_id}.html"

            if page_id in existing_ids:
                # already summarized
                continue

            # Generate user-friendly title and summary
            short_title = summarizer.generate_short_title(meeting.transcript_content)
            summary_md = summarizer.summarize(meeting.topic, meeting.transcript_content)
            
            # Format date from ISO string to readable format
            try:
                date_obj = datetime.fromisoformat(meeting.start_time.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime("%B %d, %Y")
            except:
                formatted_date = meeting.start_time[:10]  # fallback to YYYY-MM-DD
            
            user_friendly_title = f"{short_title} - {formatted_date}"

            page = MeetingPage(
                id=page_id,
                title=user_friendly_title,
                start_time=meeting.start_time,
                filename=filename,
            )
            site.write_meeting_page(page, summary_md)
            pages.append(page)
            existing_ids.add(page_id)
    else:
        # Process Zoom recordings (existing logic)
        # Date range logic
        today = dt.date.today()
        if args.from_date:
            from_date = dt.date.fromisoformat(args.from_date)
            to_date = dt.date.fromisoformat(args.to_date) if args.to_date else today
        else:
            to_date = today
            from_date = today - relativedelta(days=args.days)

        zoom = ZoomClient(cfg.zoom.access_token)
        meetings = zoom.list_recordings(from_date, to_date, cfg.zoom.host_email)

        if topics:
            meetings = [m for m in meetings if topic_matches(m.topic)]

        # Process each meeting
        for meeting in tqdm(meetings, desc="Processing Zoom meetings"):
            # Prefer AI Companion SUMMARY if available, else transcript/VTT/TXT
            transcript_url = None
            # First pass: SUMMARY
            for rf in meeting.recording_files:
                if (rf.recording_type or "").upper() == "SUMMARY" or (rf.file_type or "").upper() == "SUMMARY":
                    if rf.download_url:
                        transcript_url = rf.download_url
                        break
            # Second pass: TRANSCRIPT/VTT/TXT
            if not transcript_url:
                for rf in meeting.recording_files:
                    if (rf.recording_type or "").upper() == "TRANSCRIPT" or (rf.file_type or "").upper() in {"TRANSCRIPT", "VTT", "TXT"}:
                        if rf.download_url:
                            transcript_url = rf.download_url
                            break
            if not transcript_url:
                continue

            try:
                transcript = zoom.download_transcript_text(transcript_url)
            except Exception:
                continue

            if not transcript.strip():
                continue

            page_id = f"{meeting.meeting_id}-{meeting.start_time.replace(':', '').replace('Z', '')}"
            filename = f"meetings/{page_id}.html"

            if page_id in existing_ids:
                # already summarized
                continue

            # Generate user-friendly title and summary
            short_title = summarizer.generate_short_title(transcript)
            summary_md = summarizer.summarize(meeting.topic or "Untitled Meeting", transcript)
            
            # Format date from ISO string to readable format
            try:
                date_obj = datetime.fromisoformat(meeting.start_time.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime("%B %d, %Y")
            except:
                formatted_date = meeting.start_time[:10]  # fallback to YYYY-MM-DD
            
            user_friendly_title = f"{short_title} - {formatted_date}"

            page = MeetingPage(
                id=page_id,
                title=user_friendly_title,
                start_time=meeting.start_time,
                filename=filename,
            )
            site.write_meeting_page(page, summary_md)
            pages.append(page)
            existing_ids.add(page_id)

    # Sort newest first by start_time
    pages.sort(key=lambda p: p.start_time, reverse=True)
    site.build_index(pages)
    site.write_manifest(pages)


if __name__ == "__main__":
    main()