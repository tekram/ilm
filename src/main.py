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
    p.add_argument("--meeting-type", type=str, default=None, help="Process only this meeting type (e.g., 'tuhfa-al-muhtaaj', 'manthoma')")
    p.add_argument("--all-types", action="store_true", help="Process all configured meeting types")
    return p.parse_args()


def get_summarizer(cfg, summarizer_cache):
    """Initialize LLM summarizer only when needed (lazy initialization)"""
    if summarizer_cache[0] is None:
        # Validate LLM provider config
        if cfg.llm.provider == "openai" and not cfg.llm.openai_api_key:
            raise SystemExit("Missing OPENAI_API_KEY.")
        if cfg.llm.provider == "gemini" and not cfg.llm.gemini_api_key:
            raise SystemExit("Missing GEMINI_API_KEY.")
        
        summarizer_cache[0] = LlmSummarizer.from_config(cfg.llm)
    
    return summarizer_cache[0]


def process_meeting_type(
    meeting_type_name: str, 
    meeting_type_config, 
    cfg, 
    args, 
    site: SiteGenerator, 
    summarizer_cache: list,
    existing_ids: set,
    pages: List[MeetingPage]
) -> None:
    """Process a single meeting type"""
    recordings_dir = os.path.join(os.getcwd(), "recordings")
    local_dir = os.path.join(recordings_dir, meeting_type_config.source_dir)
    
    if not os.path.exists(local_dir):
        print(f"Directory not found for {meeting_type_name}: {local_dir}")
        return
    
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
    
    # Process local files for this meeting type
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
    for meeting in tqdm(local_meetings, desc=f"Processing {meeting_type_name}"):
        page_id = f"{meeting_type_name}-{meeting.meeting_id}"
        filename = f"{meeting_type_config.output_dir}/meetings/{meeting.meeting_id}.html"

        if page_id in existing_ids:
            # already summarized
            continue

        # Generate user-friendly title and summary (initialize LLM only when needed)
        summarizer = get_summarizer(cfg, summarizer_cache)
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
            meeting_type=meeting_type_name,
        )
        site.write_meeting_page(page, summary_md)
        pages.append(page)
        existing_ids.add(page_id)


def main() -> None:
    args = parse_args()
    cfg = load_config()

    # Determine processing mode and meeting types to process
    local_mode = args.local_dir is not None
    
    # Determine which meeting types to process
    if args.meeting_type:
        if args.meeting_type not in cfg.meeting_types:
            available_types = ", ".join(cfg.meeting_types.keys())
            raise SystemExit(f"Unknown meeting type '{args.meeting_type}'. Available types: {available_types}")
        meeting_types_to_process = [args.meeting_type]
    elif args.all_types:
        meeting_types_to_process = list(cfg.meeting_types.keys())
    else:
        # Legacy mode - if local-dir is specified, use it; otherwise process all types
        if local_mode:
            # Legacy: use the provided local directory
            meeting_types_to_process = []
        else:
            # Default: process all meeting types
            meeting_types_to_process = list(cfg.meeting_types.keys())
    
    if local_mode and not meeting_types_to_process:
        # Legacy local mode
        local_dir = args.local_dir
        if not os.path.exists(local_dir):
            raise SystemExit(f"Local directory does not exist: {local_dir}")
    elif meeting_types_to_process:
        # Multi-type mode - we're processing from local directories, no Zoom needed
        pass
    else:
        # Validate Zoom credentials for Zoom mode
        if not cfg.zoom.access_token:
            raise SystemExit("Missing Zoom access token in environment (ZOOM_ACCESS_TOKEN).")

    # Initialize clients
    site = SiteGenerator(cfg.templates_dir, cfg.docs_dir, cfg.meetings_dir, cfg.meeting_types)
    
    # Only initialize LLM if we might need it (defer validation)
    summarizer_cache = [None]  # Use list for mutable reference

    # Load existing pages to avoid reprocessing
    pages: List[MeetingPage] = site.load_manifest()
    existing_ids = {p.id for p in pages}

    if local_mode and not meeting_types_to_process:
        # Legacy local mode - process the provided directory
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

        # Process legacy local files
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
        
        # Process each local meeting (legacy format)
        for meeting in tqdm(local_meetings, desc="Processing local files"):
            page_id = meeting.meeting_id
            filename = f"meetings/{page_id}.html"

            if page_id in existing_ids:
                # already summarized
                continue

            # Generate user-friendly title and summary (initialize LLM only when needed)
            summarizer = get_summarizer(cfg, summarizer_cache)
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
    elif meeting_types_to_process:
        # New multi-type mode
        for meeting_type_name in meeting_types_to_process:
            meeting_type_config = cfg.meeting_types[meeting_type_name]
            process_meeting_type(
                meeting_type_name,
                meeting_type_config,
                cfg,
                args,
                site,
                summarizer_cache,
                existing_ids,
                pages
            )
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

            # Generate user-friendly title and summary (initialize LLM only when needed)
            summarizer = get_summarizer(cfg, summarizer_cache)
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
    
    # Build indexes
    site.build_index(pages)
    if cfg.meeting_types:
        site.build_type_indexes(pages)
    
    site.write_manifest(pages)


if __name__ == "__main__":
    main()