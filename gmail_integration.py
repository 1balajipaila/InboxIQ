from __future__ import annotations

import base64
import html
import json
import os
import threading
from email.utils import parseaddr
from html.parser import HTMLParser

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(
    BASE_DIR, os.environ.get("GMAIL_CREDENTIALS_FILE", "credentials.json")
)
TOKEN_FILE = os.path.join(
    BASE_DIR, os.environ.get("GMAIL_TOKEN_FILE", "token.json")
)
PREFERENCES_FILE = os.path.join(BASE_DIR, "preferences.json")

POLL_SECONDS = max(10, int(os.environ.get("INBOXIQ_GMAIL_POLL_SECONDS", "20")))

LABEL_INBOXIQ = "InboxIQ"
LABEL_SPAM = "InboxIQ/Spam"

_service = None
_worker = None
_stop_event = threading.Event()
_auth_lock = threading.Lock()
_oauth_running = False
_last_oauth_error = None


class _HTMLTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        if data.strip():
            self.parts.append(data.strip())

    def text(self):
        return " ".join(self.parts)


def _html_to_text(value: str) -> str:
    parser = _HTMLTextParser()
    try:
        parser.feed(value)
        parser.close()
        return " ".join(parser.parts)
    except Exception:
        return value


def _load_preferences():
    try:
        with open(PREFERENCES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        prefs = data.get("user_interests", [])
        return prefs if isinstance(prefs, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_preferences(interests):
    with open(PREFERENCES_FILE, "w", encoding="utf-8") as f:
        json.dump({"user_interests": interests}, f, indent=2)


def _get_credentials():
    global _last_oauth_error
    creds = None

    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if creds and creds.valid:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        return creds

    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            "Google OAuth credentials not found. Put your downloaded Google "
            "OAuth Desktop App JSON in the InboxIQ folder and name it "
            "'credentials.json'."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_FILE, SCOPES
    )
    creds = flow.run_local_server(
        host="127.0.0.1",
        port=0,
        open_browser=True,
        prompt="consent",
        authorization_prompt_message=(
            "Open this URL in your browser if it does not open automatically:\n{url}"
        ),
    )

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    _last_oauth_error = None
    return creds


def get_service():
    global _service
    with _auth_lock:
        creds = _get_credentials()
        _service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return _service


def is_connected():
    try:
        if not os.path.exists(TOKEN_FILE):
            return False
        service = get_service()
        service.users().getProfile(userId="me").execute()
        return True
    except Exception:
        return False


def _oauth_worker():
    global _oauth_running, _last_oauth_error
    try:
        get_service()
        ensure_labels()
        start_background_worker()
    except Exception as e:
        _last_oauth_error = str(e)
        print(f"[InboxIQ Gmail] Authorization error: {e}")
    finally:
        _oauth_running = False


def start_oauth():
    global _oauth_running
    if _oauth_running:
        return False

    _oauth_running = True
    threading.Thread(
        target=_oauth_worker,
        daemon=True,
        name="InboxIQ-Gmail-OAuth",
    ).start()
    return True


def ensure_labels():
    service = get_service()
    existing = service.users().labels().list(userId="me").execute().get("labels", [])
    by_name = {x["name"]: x["id"] for x in existing}

    ids = {}
    for name in (LABEL_INBOXIQ, LABEL_SPAM):
        if name in by_name:
            ids[name] = by_name[name]
            continue

        created = service.users().labels().create(
            userId="me",
            body={
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        ).execute()
        ids[name] = created["id"]

    return ids


def _decode_part(part):
    mime = part.get("mimeType", "")
    body = part.get("body", {}) or {}
    data = body.get("data")

    if data:
        try:
            raw = base64.urlsafe_b64decode(data.encode("utf-8"))
            text = raw.decode("utf-8", errors="replace")
            if mime == "text/html":
                return _html_to_text(text)
            return text
        except Exception:
            pass

    for child in part.get("parts", []) or []:
        result = _decode_part(child)
        if result:
            return result

    return ""


def _extract_message(message):
    payload = message.get("payload", {}) or {}
    headers = {
        h.get("name", "").lower(): h.get("value", "")
        for h in payload.get("headers", []) or []
    }

    body = _decode_part(payload)
    sender_name, sender_email = parseaddr(headers.get("from", ""))
    subject = headers.get("subject", "")

    full_text = (
        f"From: {headers.get('from', '')}\n"
        f"To: {headers.get('to', '')}\n"
        f"Subject: {subject}\n\n"
        f"{body}"
    )

    return {
        "id": message["id"],
        "thread_id": message.get("threadId"),
        "from": headers.get("from", ""),
        "sender_name": sender_name,
        "sender_email": sender_email,
        "subject": subject,
        "body": body,
        "text": full_text,
    }


def _modify_message(message_id, add_labels=None, remove_labels=None):
    service = get_service()
    return service.users().messages().modify(
        userId="me",
        id=message_id,
        body={
            "addLabelIds": add_labels or [],
            "removeLabelIds": remove_labels or [],
        },
    ).execute()


def _pipeline(email_text, user_interests):
    from app import run_pipeline
    return run_pipeline(email_text, user_interests)


def process_message(message, user_interests):
    email = _extract_message(message)
    result = _pipeline(email["text"], user_interests)
    labels = ensure_labels()

    if result["final_class"] == "INBOXIQ":
        _modify_message(
            email["id"],
            add_labels=[labels[LABEL_INBOXIQ], "INBOX"],
            remove_labels=["SPAM"],
        )
        destination = LABEL_INBOXIQ

    elif result["final_class"] == "SPAM":
        _modify_message(
            email["id"],
            add_labels=[labels[LABEL_SPAM], "SPAM"],
            remove_labels=["INBOX"],
        )
        destination = LABEL_SPAM

    else:
        destination = "Inbox"

    return {
        "message_id": email["id"],
        "from": email["from"],
        "subject": email["subject"],
        "destination": destination,
        "result": result,
    }


def process_new_mail_once():
    """
    Process unread mail currently in Gmail's Inbox.

    Important: Gmail's own pre-delivery spam system may place a message in
    Gmail Spam before InboxIQ sees it. This local integration processes
    messages that Gmail has delivered to the Inbox.
    """
    service = get_service()
    user_interests = _load_preferences()

    response = service.users().messages().list(
        userId="me",
        q="{in:inbox in:spam} is:unread",
        maxResults=25,
    ).execute()

    results = []

    for item in response.get("messages", []):
        try:
            message = service.users().messages().get(
                userId="me",
                id=item["id"],
                format="full",
            ).execute()

            result = process_message(message, user_interests)

            # Mark it read after successful classification.
            _modify_message(item["id"], remove_labels=["UNREAD"])
            results.append(result)

            print(
                f"[InboxIQ Gmail] {result['destination']} | "
                f"{result['from']} | {result['subject']}"
            )

        except Exception as e:
            print(f"[InboxIQ Gmail] Failed {item.get('id')}: {e}")

    return results


def _poll_loop():
    print(
        f"[InboxIQ Gmail] Automatic processing ON "
        f"(checking every {POLL_SECONDS} seconds)"
    )

    while not _stop_event.is_set():
        try:
            if os.path.exists(TOKEN_FILE):
                process_new_mail_once()
        except HttpError as e:
            print(f"[InboxIQ Gmail] Gmail API error: {e}")
        except Exception as e:
            print(f"[InboxIQ Gmail] Worker error: {e}")

        _stop_event.wait(POLL_SECONDS)


def start_background_worker():
    global _worker
    if _worker and _worker.is_alive():
        return

    _stop_event.clear()
    _worker = threading.Thread(
        target=_poll_loop,
        daemon=True,
        name="InboxIQ-Gmail-Worker",
    )
    _worker.start()


def stop_background_worker():
    _stop_event.set()


def status():
    connected = False
    email = None
    error = _last_oauth_error

    try:
        if os.path.exists(TOKEN_FILE):
            service = get_service()
            profile = service.users().getProfile(userId="me").execute()
            connected = True
            email = profile.get("emailAddress")
    except Exception as e:
        error = str(e)

    return {
        "connected": connected,
        "email": email,
        "oauth_running": _oauth_running,
        "worker_running": bool(_worker and _worker.is_alive()),
        "preferences": _load_preferences(),
        "poll_seconds": POLL_SECONDS,
        "error": error,
    }