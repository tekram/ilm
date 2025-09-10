from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

ZOOM_OAUTH_TOKEN_URL = "https://zoom.us/oauth/token"
ZOOM_API_BASE = "https://api.zoom.us/v2"


@dataclass
class ZoomRecordingFile:
    id: str
    file_type: str
    download_url: str
    status: Optional[str] = None
    recording_type: Optional[str] = None


@dataclass
class ZoomMeeting:
    meeting_id: str
    topic: str
    start_time: str
    host_email: Optional[str] = None
    recording_files: List[ZoomRecordingFile] = None


class ZoomClient:
    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    def _get_access_token(self) -> str:
        """Return the manually provided access token."""
        return self._access_token

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._get_access_token()}"}

    def list_recordings(
        self, from_date: dt.date, to_date: dt.date, user_id: str
    ) -> List[ZoomMeeting]:
        """List all recordings for a given Zoom user."""
        meetings: List[ZoomMeeting] = []
        params: Dict[str, Any] = {
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
            "page_size": 50,
        }

        next_page_token: Optional[str] = None
        while True:
            request_params = dict(params)
            if next_page_token:
                request_params["next_page_token"] = next_page_token

            url = f"{ZOOM_API_BASE}/users/{user_id}/recordings"
            resp = requests.get(url, headers=self._headers(), params=request_params, timeout=30)

            if not resp.ok:
                print(f"Zoom API Error {resp.status_code}: {resp.text}")
                print(f"URL: {resp.url}")
            resp.raise_for_status()

            data = resp.json()
            for m in data.get("meetings", []):
                rec_files = [
                    ZoomRecordingFile(
                        id=str(rf.get("id")),
                        file_type=rf.get("file_type"),
                        download_url=rf.get("download_url"),
                        status=rf.get("status"),
                        recording_type=rf.get("recording_type"),
                    )
                    for rf in m.get("recording_files", [])
                ]

                meetings.append(
                    ZoomMeeting(
                        meeting_id=str(m.get("id")),
                        topic=m.get("topic", ""),
                        start_time=m.get("start_time", ""),
                        host_email=m.get("host_email"),
                        recording_files=rec_files,
                    )
                )

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

        return meetings

    def download_transcript_text(self, download_url: str) -> str:
        """Download transcript text (VTT → plain text)."""
        resp = requests.get(download_url, headers=self._headers(), timeout=60)
        resp.raise_for_status()
        content = resp.text
        if content.strip().startswith("WEBVTT"):
            return _vtt_to_text(content)
        return content


def _vtt_to_text(vtt: str) -> str:
    """Convert a WEBVTT transcript to plain text."""
    lines: List[str] = []
    for raw in vtt.splitlines():
        line = raw.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line or line.isdigit():
            continue
        lines.append(line)
    return "\n".join(lines)
