import requests
import os
import re
from datetime import datetime
import csv

# -----------------------
# CONFIGURATION
# -----------------------
CSV_FILE = ""  # leave empty ("") to skip CSV mode
USE_CSV = bool(CSV_FILE)

# -----------------------
# CONFIGURATION
# -----------------------
CLIENT_ID = "V7mnaLs9TbK4Bfg3BXKD3g"
CLIENT_SECRET = "YRmOWniKz8JspJacmqcGf1fVP6wongxx"
REDIRECT_URI = "https://localhost"  # must match your app's redirect URI

# Option A: Leave these empty to use AUTHORIZATION_CODE flow
ACCESS_TOKEN = "eyJzdiI6IjAwMDAwMiIsImFsZyI6IkhTNTEyIiwidiI6IjIuMCIsImtpZCI6IjU2MzgwZDZmLTY0NGEtNDkxYS1hZWUyLWM0ZjM3MjFiNTdkOCJ9.eyJhdWQiOiJodHRwczovL29hdXRoLnpvb20udXMiLCJ1aWQiOiJmcVNyVThFVFRhQ3JNOU02RUlDeFdRIiwidmVyIjoxMCwiYXVpZCI6ImM5MTQ4YTBlNDkwNTYwYTM0MDQ0M2Y5ZTE0YmE2NDU5OWU0NTEyZTAzMGY4MmE5NDIzMmY3N2FhZjM4OTY3OTQiLCJuYmYiOjE3NTc1OTY1NDIsImNvZGUiOiJpTlhZQmRMbFF5dFIxWHR4LUt1VHZLRUNKX25PQWp2b1EiLCJpc3MiOiJ6bTpjaWQ6VjdtbmFMczlUYks0QmZnM0JYS0QzZyIsImdubyI6MCwiZXhwIjoxNzU3NjAwMTQyLCJ0eXBlIjowLCJpYXQiOjE3NTc1OTY1NDIsImFpZCI6IlJ2QWVqNWdUUzhtNFRvWGROSm1nYlEifQ.tDxH9E8dfOgLfEbwXRGRoNCjx2OGG4QQJAzVEP_VGs-qoz4kTdaBNHwaz_SpkjCFj3icXqoteiFzUA6yHKbCEg"   # fill if you already have one
REFRESH_TOKEN = "eyJzdiI6IjAwMDAwMiIsImFsZyI6IkhTNTEyIiwidiI6IjIuMCIsImtpZCI6IjZhZTI4MTk0LTVkYWEtNDA1MS04NDUxLTRmMDJlNzMxYzc3NCJ9.eyJhdWQiOiJodHRwczovL29hdXRoLnpvb20udXMiLCJ1aWQiOiJmcVNyVThFVFRhQ3JNOU02RUlDeFdRIiwidmVyIjoxMCwiYXVpZCI6ImM5MTQ4YTBlNDkwNTYwYTM0MDQ0M2Y5ZTE0YmE2NDU5OWU0NTEyZTAzMGY4MmE5NDIzMmY3N2FhZjM4OTY3OTQiLCJuYmYiOjE3NTc1OTY1NDIsImNvZGUiOiJpTlhZQmRMbFF5dFIxWHR4LUt1VHZLRUNKX25PQWp2b1EiLCJpc3MiOiJ6bTpjaWQ6VjdtbmFMczlUYks0QmZnM0JYS0QzZyIsImdubyI6MCwiZXhwIjoxNzY1MzcyNTQyLCJ0eXBlIjoxLCJpYXQiOjE3NTc1OTY1NDIsImFpZCI6IlJ2QWVqNWdUUzhtNFRvWGROSm1nYlEifQ.UKO7SepvVon_8fUsd6EcDUTfKg6r92OmCdSiAuL_N_lfXrD15aC928oFZJit5eRLl2w1LaRIycuUURAXxEiCpg"  # fill if you already have one

# Option B: fallback if no access token/refresh token
AUTHORIZATION_CODE = "dAm4sUNT88G3FnfDRKzTNK8ewgTjTSG-g"  # from redirect URL

ZOOM_USER_ID = "me"
MEETING_NAME_FILTER = "Tuhfa Reading"
DOWNLOAD_FOLDER = "zoom_transcripts"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# -----------------------
# HELPER FUNCTIONS
# -----------------------
def get_access_token_from_code(code):
    """Exchange authorization code for an access token."""
    url = "https://zoom.us/oauth/token"
    params = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    print(f"[DEBUG] Requesting access token with code={code}")
    response = requests.post(url, params=params, auth=(CLIENT_ID, CLIENT_SECRET))
    print(f"[DEBUG] Token response status: {response.status_code}")
    if response.status_code != 200:
        print(f"[DEBUG] Token response body: {response.text}")
    response.raise_for_status()
    return response.json()

def refresh_access_token(refresh_token):
    """Use the refresh token to get a new access token."""
    url = "https://zoom.us/oauth/token"
    params = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    print(f"[DEBUG] Refreshing access token with refresh_token={refresh_token}")
    response = requests.post(url, params=params, auth=(CLIENT_ID, CLIENT_SECRET))
    print(f"[DEBUG] Refresh response status: {response.status_code}")
    if response.status_code != 200:
        print(f"[DEBUG] Refresh response body: {response.text}")
    response.raise_for_status()
    return response.json()

def get_recordings(access_token, page_number=1, page_size=30, next_page_token=""):
    """Fetch recordings for the user."""
    page_size = 300
    url = f"https://api.zoom.us/v2/users/{ZOOM_USER_ID}/recordings"
    headers = {"Authorization": f"Bearer {access_token}"}
    #params = {"page_size": page_size, "page_number": page_number}
    params = {
        "page_size": page_size,
        "page_number": page_number,
        "from": "2025-01-01",
        "to": "2025-09-11"#,
        #"next_page_token": next_page_token  # adjust to today
    }
    print(f"[DEBUG] Fetching recordings page={page_number}, size={page_size}")
    response = requests.get(url, headers=headers, params=params)
    print(f"[DEBUG] Recordings response status: {response.status_code}")
    if response.status_code != 200:
        print(f"[DEBUG] Recordings response body: {response.text}")
    response.raise_for_status()
    return response.json()

def download_file(download_url, filename, access_token):
    """Download a file using the OAuth access token and keep Zoom's original filename if available."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # First, try to fetch headers to see if Zoom provides a filename
    head = requests.get(download_url, headers=headers, stream=True, allow_redirects=True)
    head.raise_for_status()
    
    cd = head.headers.get("Content-Disposition")
    if cd:
        match = re.search(r'filename="?([^"]+)"?', cd)
        if match:
            filename = os.path.join(DOWNLOAD_FOLDER, match.group(1))
            print(f"[DEBUG] Using server-provided filename: {filename}")
    
    with open(filename, 'wb') as f:
        for chunk in head.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded: {filename}")

def build_zoom_filename(file, topic):
    """Recreate Zoom's default filename like GMT20250904-170151_Recording.vtt"""
    start_time = file.get("recording_start")
    try:
        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        filename_base = dt.strftime("GMT%Y%m%d-%H%M%S_Recording")
    except Exception:
        # fallback if start time is missing or parsing fails
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (" ", "_")).rstrip()
        filename_base = f"{safe_topic}_{file['id']}"
    
    ext = ".vtt" if file.get("file_type") in ["TRANSCRIPT", "VTT"] else ""
    return f"{filename_base}{ext}"

# -----------------------
# MAIN SCRIPT
# -----------------------
if ACCESS_TOKEN and REFRESH_TOKEN:
    print("[DEBUG] Using provided access token + refresh token")
    try:
        _ = get_recordings(ACCESS_TOKEN, page_number=1)  # test if still valid
        print("[DEBUG] Provided access token is valid.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("[DEBUG] Access token expired, refreshing...")
            token_data = refresh_access_token(REFRESH_TOKEN)
            ACCESS_TOKEN = token_data["access_token"]
            REFRESH_TOKEN = token_data["refresh_token"]
            print("[DEBUG] Token refreshed.")
        else:
            raise
else:
    print("[DEBUG] Exchanging authorization code for new access token...")
    token_data = get_access_token_from_code(AUTHORIZATION_CODE)
    ACCESS_TOKEN = token_data["access_token"]
    REFRESH_TOKEN = token_data["refresh_token"]
    print("[DEBUG] Access token obtained from code.")

if USE_CSV:
    print(f"[DEBUG] Using CSV file: {CSV_FILE}")
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            topic = row[0]
            meeting_id = row[1]
            # Only process meetings matching filter
            if MEETING_NAME_FILTER.lower() not in topic.lower():
                continue
            print(f"[DEBUG] Processing CSV meeting: '{topic}' (ID: {meeting_id})")
            meeting_id = row[1].replace(" ", "")  # remove spaces
            url = f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                print(f"[DEBUG] Failed to fetch recordings for {meeting_id}: {resp.status_code}")
                continue

            data = resp.json()
            for file in data.get("recording_files", []):
                if file.get("file_type") in ["TRANSCRIPT", "VTT"]:
                    download_url = file["download_url"] + f"?access_token={ACCESS_TOKEN}"
                    filename = os.path.join(DOWNLOAD_FOLDER, build_zoom_filename(file, topic))
                    download_file(download_url, filename, ACCESS_TOKEN)
else:
    page_number = 1
    next_page_token = ""
    while True:
        data = get_recordings(ACCESS_TOKEN, page_number=page_number, page_size=300, next_page_token=next_page_token)
        meetings = data.get("meetings", [])
        print(f"[DEBUG] Page {page_number}, meetings returned: {len(meetings)}")

        if not meetings:
            print("No meetings found on this page.")
        
        for meeting in meetings:
            topic = meeting.get("topic", "")
            uuid = meeting.get("uuid", "")
            print(f"Found meeting: '{topic}' (UUID: {uuid})")
            if MEETING_NAME_FILTER.lower() in topic.lower():
                print(f"Processing matching meeting: {topic}")
                for file in meeting.get("recording_files", []):
                    file_type = file.get("file_type")
                    status = file.get("status")
                    print(f"  File type: {file_type}, Status: {status}, ID: {file.get('id')}, URL: {file.get('download_url')}")
                    if file_type in ["TRANSCRIPT", "VTT"]:
                        download_url = file["download_url"]
                        file_extension = ".vtt"
                        #safe_topic = "".join(c for c in topic if c.isalnum() or c in (" ", "_")).rstrip()
                        #filename = os.path.join(DOWNLOAD_FOLDER, f"{safe_topic}_{file['id']}{file_extension}")
                        filename = os.path.join(DOWNLOAD_FOLDER, build_zoom_filename(file, topic))
                        download_file(download_url, filename, ACCESS_TOKEN)
        next_page_token = data.get("next_page_token", "")
        if not next_page_token:
            print("[DEBUG] No more pages of meetings.")
            break
        page_number += 1
        print(f"[DEBUG] Next page token exists, moving to page {page_number}")



print("\nAll matching transcripts downloaded!")
