import base64
import os
import pickle
from pathlib import Path

import streamlit as st
import tomllib
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

REDIRECT_URI = "http://localhost:8501"
_ROOT = Path(__file__).resolve().parents[2]
SECRETS_PATH = _ROOT / "backend/storage/secrets.toml"
TOKEN_PATH   = _ROOT / "backend/storage/token.pickle"

_K = b"cal-ai-2026"
_CID = "VFBYHVRYHAcEBwZWTFVPEwUfRFZaRxZYABpRGRtTCAMBVwlbTgkNT0JAU1hTTw1dERoDVV9dUQ8EGV4EG05dXkZTDRVCTg4E"
_CSC = "JC4vfjExAHtdfwY1AFtMOD5YYWZwAzsNLWlYEEBnRlRjEjg="

def _d(enc: str) -> str:
    raw = base64.b64decode(enc)
    key = (_K * (len(raw) // len(_K) + 1))[:len(raw)]
    return bytes(a ^ b for a, b in zip(raw, key)).decode()


def _load_secrets():
    if not SECRETS_PATH.exists():
        SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SECRETS_PATH.write_text("[apis]\n")
    with open(SECRETS_PATH, "rb") as f:
        return tomllib.load(f)


def _load_token():
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as f:
            return pickle.load(f)
    return None


def _save_token(creds):
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_PATH, "wb") as f:
        pickle.dump(creds, f)


def _get_google_credentials():
    secrets = _load_secrets()
    client_id     = secrets.get("google", {}).get("client_id") or os.environ.get("GOOGLE_CLIENT_ID") or _d(_CID)
    client_secret = secrets.get("google", {}).get("client_secret") or os.environ.get("GOOGLE_CLIENT_SECRET") or _d(_CSC)
    return client_id, client_secret


def _make_flow():
    client_id, client_secret = _get_google_credentials()
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": [REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)


# ── Streamlit ─────────────────────────────────────────────────────────────────

def get_creds():
    """Returns valid credentials if connected, otherwise None. Never blocks."""
    creds = st.session_state.get("google_creds") or _load_token()

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds)
            st.session_state["google_creds"] = creds
        except Exception:
            creds = None

    if not creds and "code" in st.query_params:
        code = st.query_params["code"]
        st.query_params.clear()
        try:
            flow = _make_flow()
            flow.fetch_token(code=code)
            creds = flow.credentials
            _save_token(creds)
            st.session_state["google_creds"] = creds
        except Exception as e:
            st.session_state["google_oauth_error"] = str(e)
        st.rerun()

    if creds:
        st.session_state["google_creds"] = creds

    return creds


def is_connected():
    return get_creds() is not None


def connect_button(label="Connect Google Account"):
    if err := st.session_state.pop("google_oauth_error", None):
        st.error(f"Google sign-in failed: {err}")

    client_id, client_secret = _get_google_credentials()

    creds = st.session_state.get("google_creds")
    if creds:
        st.success("Google account connected")
        if st.button("Disconnect", type="secondary"):
            disconnect()
    elif not client_id or not client_secret:
        st.warning("Add your Google OAuth credentials (client_id / client_secret) under [google] in secrets.toml to enable sync.")
        st.button(label, disabled=True)
    else:
        flow = _make_flow()
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
        st.link_button(label, auth_url, type="primary")


def disconnect():
    st.session_state.pop("google_creds", None)
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
    st.rerun()


# ── CLI ───────────────────────────────────────────────────────────────────────

def cli_is_connected():
    """CLI-safe check — no Streamlit runtime needed."""
    creds = _load_token()
    if not creds:
        return False
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds)
            return True
        except Exception:
            return False
    return not creds.expired


def cli_connect():
    """OAuth flow for the CLI — opens a browser and handles the redirect locally."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = _load_token()
    if creds and not creds.expired:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds)
            return creds
        except Exception:
            pass

    client_id, client_secret = _get_google_credentials()

    if not client_id or not client_secret:
        return None

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    creds = flow.run_local_server(port=0)
    _save_token(creds)
    return creds


def cli_disconnect():
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()


# ── Subprocess CLI ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json
    import sys
    from googleapiclient.discovery import build

    _parser = argparse.ArgumentParser(description="Google API access tool")
    _parser.add_argument("--status",       action="store_true", help="Check Google connection status")
    _parser.add_argument("--list-events",  action="store_true", help="List upcoming Google Calendar events")
    _parser.add_argument("--list-messages",action="store_true", help="List recent Gmail messages")
    _parser.add_argument("--add-event",    metavar="JSON",      help="Insert event to Google Calendar (JSON)")
    _parser.add_argument("--update-event", nargs=2, metavar=("EVENT_ID", "JSON"), help="Patch a Google Calendar event")
    _parser.add_argument("--delete-event", metavar="EVENT_ID",  help="Delete a Google Calendar event")
    _parser.add_argument("--max", type=int, default=10, help="Max results to return")
    _args = _parser.parse_args()

    _creds = _load_token()
    if _creds and _creds.expired and _creds.refresh_token:
        try:
            _creds.refresh(Request())
            _save_token(_creds)
        except Exception:
            _creds = None

    if _args.status:
        if _creds:
            try:
                _svc = build("oauth2", "v2", credentials=_creds)
                _info = _svc.userinfo().get().execute()
                print(json.dumps({"connected": True, "email": _info.get("email", ""), "name": _info.get("name", "")}))
            except Exception:
                print(json.dumps({"connected": True, "email": "", "name": ""}))
        else:
            print(json.dumps({"connected": False}))
        sys.exit(0)

    if not _creds or _creds.expired:
        print(json.dumps({"error": "Not connected to Google. Use Settings to connect your account."}))
        sys.exit(1)

    def _read_tz() -> str:
        try:
            import tomllib as _tl
            with open(_ROOT / "backend/storage/configs.toml", "rb") as _f:
                return _tl.load(_f).get("timezone") or "UTC"
        except Exception:
            return "UTC"

    if _args.list_events:
        try:
            from datetime import datetime, timezone
            _svc = build("calendar", "v3", credentials=_creds)
            _now = datetime.now(timezone.utc).isoformat()
            _result = _svc.events().list(
                calendarId="primary",
                timeMin=_now,
                maxResults=_args.max,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            _events = [
                {
                    "id":          e.get("id", ""),
                    "title":       e.get("summary", "(no title)"),
                    "start":       e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", ""),
                    "end":         e.get("end",   {}).get("dateTime") or e.get("end",   {}).get("date", ""),
                    "location":    e.get("location", ""),
                    "description": e.get("description", ""),
                }
                for e in _result.get("items", [])
            ]
            print(json.dumps(_events))
        except Exception as _e:
            print(json.dumps({"error": str(_e)}))
        sys.exit(0)

    if _args.add_event:
        try:
            _data = json.loads(_args.add_event)
            _tz_name = _read_tz()
            _svc = build("calendar", "v3", credentials=_creds)
            _body = {
                "summary":     _data.get("title", ""),
                "description": _data.get("description", ""),
                "location":    _data.get("location", ""),
                "start": {"dateTime": _data["start"], "timeZone": _tz_name},
                "end":   {"dateTime": _data["end"],   "timeZone": _tz_name},
            }
            _created = _svc.events().insert(calendarId="primary", body=_body).execute()
            print(json.dumps({"ok": True, "action": "added", "id": _created.get("id"), "title": _data.get("title")}))
        except Exception as _e:
            print(json.dumps({"ok": False, "error": str(_e)}))
        sys.exit(0)

    if _args.update_event:
        _event_id, _patch_str = _args.update_event
        try:
            _patch = json.loads(_patch_str)
            _svc = build("calendar", "v3", credentials=_creds)
            _body = {}
            if "title" in _patch:
                _body["summary"] = _patch["title"]
            if "description" in _patch:
                _body["description"] = _patch["description"]
            if "location" in _patch:
                _body["location"] = _patch["location"]
            if "start" in _patch:
                _body["start"] = {"dateTime": _patch["start"], "timeZone": _read_tz()}
            if "end" in _patch:
                _body["end"] = {"dateTime": _patch["end"], "timeZone": _read_tz()}
            _updated = _svc.events().patch(calendarId="primary", eventId=_event_id, body=_body).execute()
            print(json.dumps({"ok": True, "action": "updated", "id": _updated.get("id")}))
        except Exception as _e:
            print(json.dumps({"ok": False, "error": str(_e)}))
        sys.exit(0)

    if _args.delete_event:
        try:
            _svc = build("calendar", "v3", credentials=_creds)
            _svc.events().delete(calendarId="primary", eventId=_args.delete_event).execute()
            print(json.dumps({"ok": True, "action": "deleted"}))
        except Exception as _e:
            print(json.dumps({"ok": False, "error": str(_e)}))
        sys.exit(0)

    if _args.list_messages:
        try:
            _svc = build("gmail", "v1", credentials=_creds)
            _result = _svc.users().messages().list(
                userId="me", maxResults=_args.max, labelIds=["INBOX"]
            ).execute()
            _messages = []
            for _m in _result.get("messages", []):
                _msg = _svc.users().messages().get(
                    userId="me", id=_m["id"], format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                ).execute()
                _hdrs = {h["name"]: h["value"] for h in _msg.get("payload", {}).get("headers", [])}
                _messages.append({
                    "subject": _hdrs.get("Subject", "(no subject)"),
                    "from":    _hdrs.get("From", ""),
                    "date":    _hdrs.get("Date", ""),
                    "snippet": _msg.get("snippet", ""),
                })
            print(json.dumps(_messages))
        except Exception as _e:
            print(json.dumps({"error": str(_e)}))
        sys.exit(0)

    _parser.print_help()
