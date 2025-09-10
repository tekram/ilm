from __future__ import annotations

import os
import datetime as dt
import re
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass
class LocalTranscriptFile:
    """Represents a local transcript file."""
    file_path: str
    filename: str
    modified_time: dt.datetime
    size_bytes: int


@dataclass
class LocalMeeting:
    """Represents a local meeting derived from a transcript file."""
    meeting_id: str  # Based on filename
    topic: str  # Derived from filename
    start_time: str  # ISO format from file modification time
    transcript_content: str
    file_path: str


class LocalFileClient:
    """Client for processing local transcript files."""
    
    def __init__(self, directory_path: str) -> None:
        self.directory_path = Path(directory_path)
        if not self.directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")
        if not self.directory_path.is_dir():
            raise ValueError(f"Path is not a directory: {directory_path}")
    
    def list_transcript_files(self) -> List[LocalTranscriptFile]:
        """List all transcript files in the directory."""
        transcript_files: List[LocalTranscriptFile] = []
        
        # Support common transcript file extensions
        supported_extensions = {'.txt', '.vtt', '.srt', '.transcript'}
        
        for file_path in self.directory_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                stat = file_path.stat()
                transcript_files.append(LocalTranscriptFile(
                    file_path=str(file_path),
                    filename=file_path.name,
                    modified_time=dt.datetime.fromtimestamp(stat.st_mtime),
                    size_bytes=stat.st_size
                ))
        
        # Sort by modification time, newest first
        transcript_files.sort(key=lambda x: x.modified_time, reverse=True)
        return transcript_files
    
    def load_transcript_content(self, file_path: str) -> str:
        """Load and process transcript content from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # If it's a VTT file, convert to plain text
        if content.strip().startswith("WEBVTT"):
            return self._vtt_to_text(content)
        
        return content.strip()
    
    def create_meeting_from_file(self, transcript_file: LocalTranscriptFile) -> Optional[LocalMeeting]:
        """Create a LocalMeeting object from a transcript file."""
        try:
            transcript_content = self.load_transcript_content(transcript_file.file_path)
            
            if not transcript_content.strip():
                return None
            
            # Generate meeting ID from filename and modification time
            filename_base = Path(transcript_file.filename).stem
            meeting_id = f"local-{filename_base}-{transcript_file.modified_time.strftime('%Y%m%d%H%M%S')}"
            
            # Extract topic from filename (remove extension and common prefixes/suffixes)
            topic = self._extract_topic_from_filename(filename_base)
            
            # Extract date from filename, fallback to modification time
            extracted_date = self._extract_date_from_filename(filename_base)
            if extracted_date:
                start_time = extracted_date.isoformat()
            else:
                start_time = transcript_file.modified_time.isoformat()
            
            return LocalMeeting(
                meeting_id=meeting_id,
                topic=topic,
                start_time=start_time,
                transcript_content=transcript_content,
                file_path=transcript_file.file_path
            )
            
        except Exception as e:
            print(f"Error processing file {transcript_file.file_path}: {e}")
            return None
    
    def _extract_date_from_filename(self, filename_base: str) -> Optional[dt.datetime]:
        """Extract date from filename patterns like GMT20250626-170028 or similar."""
        # Pattern 1: GMT20250626-170028 (GMT + YYYYMMDD + - + HHMMSS)
        pattern1 = r'GMT(\d{8})-(\d{6})'
        match1 = re.search(pattern1, filename_base)
        if match1:
            date_str, time_str = match1.groups()
            try:
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                hour = int(time_str[:2])
                minute = int(time_str[2:4])
                second = int(time_str[4:6])
                return dt.datetime(year, month, day, hour, minute, second)
            except ValueError:
                pass
        
        # Pattern 2: YYYYMMDD anywhere in filename
        pattern2 = r'(\d{8})'
        match2 = re.search(pattern2, filename_base)
        if match2:
            date_str = match2.group(1)
            try:
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                # Use noon as default time if no time in filename
                return dt.datetime(year, month, day, 12, 0, 0)
            except ValueError:
                pass
        
        # Pattern 3: YYYY-MM-DD format
        pattern3 = r'(\d{4}-\d{2}-\d{2})'
        match3 = re.search(pattern3, filename_base)
        if match3:
            date_str = match3.group(1)
            try:
                return dt.datetime.fromisoformat(date_str + 'T12:00:00')
            except ValueError:
                pass
        
        return None

    def _extract_topic_from_filename(self, filename_base: str) -> str:
        """Extract a readable topic from the filename."""
        # Remove common prefixes and suffixes
        topic = filename_base
        
        # Remove date patterns first
        topic = re.sub(r'GMT\d{8}-\d{6}', '', topic)
        topic = re.sub(r'\d{8}', '', topic)
        topic = re.sub(r'\d{4}-\d{2}-\d{2}', '', topic)
        
        # Remove common patterns
        patterns_to_remove = [
            'transcript', 'recording', 'meeting', 'call', 'session',
            'zoom', 'teams', 'webex'
        ]
        
        for pattern in patterns_to_remove:
            topic = topic.replace(pattern.lower(), '').replace(pattern.upper(), '')
        
        # Replace underscores and hyphens with spaces
        topic = topic.replace('_', ' ').replace('-', ' ')
        
        # Clean up multiple spaces
        topic = ' '.join(topic.split())
        
        # Capitalize words
        topic = topic.title()
        
        return topic if topic.strip() else "Local Meeting"
    
    def _vtt_to_text(self, vtt: str) -> str:
        """Convert a WEBVTT transcript to plain text."""
        lines: List[str] = []
        for raw in vtt.splitlines():
            line = raw.strip()
            if not line or line.startswith("WEBVTT") or "-->" in line or line.isdigit():
                continue
            lines.append(line)
        return "\n".join(lines)
