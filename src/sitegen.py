from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape


@dataclass
class MeetingPage:
    id: str
    title: str
    start_time: str
    filename: str  # relative to docs/
    meeting_type: str = "default"  # for backward compatibility


class SiteGenerator:
    def __init__(self, templates_dir: str, docs_dir: str, meetings_dir: str = None, meeting_types: Dict = None) -> None:
        self.templates_dir = templates_dir
        self.docs_dir = docs_dir
        self.meetings_dir = meetings_dir  # legacy - kept for compatibility
        self.meeting_types = meeting_types or {}
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        # Add custom markdown filter
        self.env.filters['markdown_to_html'] = self._markdown_to_html
        os.makedirs(self.docs_dir, exist_ok=True)
        if self.meetings_dir:
            os.makedirs(self.meetings_dir, exist_ok=True)
        
        # Create directories for each meeting type
        for meeting_type in self.meeting_types.values():
            type_dir = os.path.join(self.docs_dir, meeting_type.output_dir)
            meetings_dir = os.path.join(type_dir, "meetings")
            os.makedirs(meetings_dir, exist_ok=True)

    def write_meeting_page(self, meeting: MeetingPage, summary_markdown: str) -> None:
        template = self.env.get_template("meeting.html.j2")
        html = template.render(title=meeting.title, start_time=meeting.start_time, content_md=summary_markdown)
        out_path = os.path.join(self.docs_dir, meeting.filename)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

    def build_index(self, pages: List[MeetingPage]) -> None:
        """Build the main index page with navigation to meeting type indexes"""
        if self.meeting_types:
            # Multi-type mode: build main index with links to type-specific indexes
            template = self.env.get_template("main_index.html.j2")
            html = template.render(meeting_types=self.meeting_types)
            out_path = os.path.join(self.docs_dir, "index.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)
        else:
            # Legacy mode: single index with all pages
            template = self.env.get_template("index.html.j2")
            html = template.render(pages=pages)
            out_path = os.path.join(self.docs_dir, "index.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)
    
    def build_type_indexes(self, pages: List[MeetingPage]) -> None:
        """Build separate index pages for each meeting type"""
        if not self.meeting_types:
            return
            
        # Group pages by meeting type
        pages_by_type = {}
        for page in pages:
            meeting_type = page.meeting_type
            if meeting_type not in pages_by_type:
                pages_by_type[meeting_type] = []
            pages_by_type[meeting_type].append(page)
        
        # Build index for each type
        template = self.env.get_template("type_index.html.j2")
        for type_name, type_config in self.meeting_types.items():
            type_pages = pages_by_type.get(type_name, [])
            # Sort newest first
            type_pages.sort(key=lambda p: p.start_time, reverse=True)
            
            html = template.render(
                pages=type_pages, 
                meeting_type=type_config,
                type_name=type_name
            )
            
            out_path = os.path.join(self.docs_dir, type_config.output_dir, "index.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)

    def write_manifest(self, pages: List[MeetingPage]) -> None:
        manifest_path = os.path.join(self.docs_dir, "manifest.json")
        data = [asdict(p) for p in pages]
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_manifest(self) -> List[MeetingPage]:
        manifest_path = os.path.join(self.docs_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return []
        with open(manifest_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return [MeetingPage(**item) for item in raw]

    def _markdown_to_html(self, markdown_text: str) -> str:
        """Convert basic markdown to HTML."""
        if not markdown_text:
            return ""
        
        html = markdown_text
        
        # Convert headers (order matters - start with most specific)
        html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # Convert bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Convert code blocks
        html = re.sub(r'```(.+?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
        
        # Convert horizontal rules
        html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)
        
        # Convert bullet points
        lines = html.split('\n')
        in_list = False
        result_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('- '):
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                result_lines.append(f'<li>{stripped[2:].strip()}</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                if stripped:
                    # Don't wrap headers, hr, pre, or list elements in paragraphs
                    if not (stripped.startswith('<h') or stripped.startswith('<hr') or stripped.startswith('<pre') or stripped.startswith('<ul') or stripped.startswith('</ul') or stripped.startswith('<li')):
                        result_lines.append(f'<p>{stripped}</p>')
                    else:
                        result_lines.append(stripped)
                else:
                    result_lines.append('')
        
        if in_list:
            result_lines.append('</ul>')
        
        # Clean up empty paragraphs and extra spacing
        html = '\n'.join(result_lines)
        html = re.sub(r'<p></p>', '', html)
        html = re.sub(r'\n\s*\n', '\n', html)
        
        return html


