import requests
import os

# -----------------------
# CONFIGURATION
# -----------------------
CLIENT_ID = "V7mnaLs9TbK4Bfg3BXKD3g"
CLIENT_SECRET = "YRmOWniKz8JspJacmqcGf1fVP6wongxx"
REDIRECT_URI = "https://localhost"  # must match your app's redirect URI
AUTHORIZATION_CODE = "dAm4sUNT88G3FnfDRKzTNK8ewgTjTSG-g"  # from redirect URL

ZOOM_USER_ID = "me"  # or replace with actual user ID
MEETING_NAME_FILTER = "Tuhfa Reading"
DOWNLOAD_FOLDER = "zoom_transcripts"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# -----------------------
# HELPER FUNCTIONS
# -----------------------
def get_access_token(code):
    """Exchange authorization code for an access token."""
    url = "https://zoom.us/oauth/token"
    params = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    response = requests.post(url, params=params, auth=(CLIENT_ID, CLIENT_SECRET))
    response.raise_for_status()
    return response.json()["access_token"]

def get_recordings(access_token, page_number=1, page_size=30):
    """Fetch recordings for the user."""
    url = f"https://api.zoom.us/v2/users/{ZOOM_USER_ID}/recordings"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"page_size": page_size, "page_number": page_number}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def download_file(download_url, filename, access_token):
    """Download a file using the OAuth access token."""
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(download_url, headers=headers, stream=True)
    r.raise_for_status()
    with open(filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded: {filename}")

# -----------------------
# MAIN SCRIPT
# -----------------------
print("Exchanging authorization code for access token...")
ACCESS_TOKEN = get_access_token(AUTHORIZATION_CODE)
print("Access token obtained!\n")

page_number = 1
while True:
    data = get_recordings(ACCESS_TOKEN, page_number=page_number)
    meetings = data.get("meetings", [])

    if not meetings:
        print("No meetings found on this page.")
    
    for meeting in meetings:
        topic = meeting.get("topic", "")
        print(f"Found meeting: {topic}")  # DEBUG: print all meeting topics
        if MEETING_NAME_FILTER.lower() in topic.lower():
            print(f"Processing matching meeting: {topic}")
            for file in meeting.get("recording_files", []):
                file_type = file.get("file_type")
                print(f"  File type: {file_type}, Filename: {file.get('id')}")  # DEBUG: show all file types
                if file_type in ["TRANSCRIPT", "VTT"]:
                    download_url = file["download_url"]
                    file_extension = ".vtt"
                    safe_topic = "".join(c for c in topic if c.isalnum() or c in (" ", "_")).rstrip()
                    filename = os.path.join(DOWNLOAD_FOLDER, f"{safe_topic}_{file['id']}{file_extension}")
                    download_file(download_url + f"?access_token={ACCESS_TOKEN}", filename)

    if "next_page_token" in data and data["next_page_token"]:
        page_number += 1
    else:
        break

print("\nAll matching transcripts downloaded!")
