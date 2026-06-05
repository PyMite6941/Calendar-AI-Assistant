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


def _load_secrets():
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


def _make_flow():
    secrets = _load_secrets()
    client_id     = secrets.get("google", {}).get("client_id", "")
    client_secret = secrets.get("google", {}).get("client_secret", "")
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
        try:
            flow = _make_flow()
            flow.fetch_token(code=st.query_params["code"])
            creds = flow.credentials
            _save_token(creds)
            st.session_state["google_creds"] = creds
        except Exception:
            pass
        st.query_params.clear()
        st.rerun()

    if creds:
        st.session_state["google_creds"] = creds

    return creds


def is_connected():
    return get_creds() is not None


def connect_button(label="Connect Google Account"):
    secrets = _load_secrets()
    client_id     = secrets.get("google", {}).get("client_id", "")
    client_secret = secrets.get("google", {}).get("client_secret", "")

    creds = get_creds()
    if creds:
        st.success("Google account connected")
        if st.button("Disconnect", type="secondary"):
            disconnect()
    elif not client_id or not client_secret:
        st.warning("Google OAuth not configured in secrets.toml")
    else:
        flow = _make_flow()
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
        st.link_button(label, auth_url)


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

    secrets = _load_secrets()
    client_id     = secrets.get("google", {}).get("client_id", "")
    client_secret = secrets.get("google", {}).get("client_secret", "")

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
