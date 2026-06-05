# Modules for functionality
import json
import shutil
import streamlit as st
from streamlit_calendar import calendar
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.auth.add_google_oauth import connect_button, get_creds

def get_calendar_events():
    result = subprocess.run(["python", "backend/tools/calendar_events.py", "--get"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    try:
        return json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []

def get_config(key, default=None, path=None):
    cmd = ["python", "backend/tools/config_editing.py", "--key", key, "--default", str(default)]
    if path:
        cmd += ["--path", path]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    return result.stdout.strip()

def set_config(key, value, path="backend/storage/configs.toml"):
    subprocess.run(["python", "backend/tools/config_editing.py", "--key", key, "--set", str(value), "--path", path], capture_output=True, text=True, cwd=str(PROJECT_ROOT))

def get_todo_list():
    result = subprocess.run(["python", "backend/tools/todo_stuff.py", "--get"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    try:
        return json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []

st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")

# Handle Google OAuth callback on every page load
get_creds()

if not st.session_state.get("initialized", False):
    st.session_state["initialized"] = True
    st.session_state["calendar"] = get_calendar_events()
    st.session_state["calendar_view"] = get_config("calendar_view", "dayGridMonth")
    st.session_state["todo_list"] = get_todo_list()
    st.session_state["chat_history"] = []

def description_page():
    st.title("Description of this project")
    readme = PROJECT_ROOT / "README.md"
    st.markdown(readme.read_text() if readme.exists() else "_No description yet._")

def calendar_page():
    st.title("Your Calendar, AI Managed")

    calendar_options = {
        "initialView": st.session_state["calendar_view"],
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay",
        },
        "selectable": True,
    }

    calendar(
        events=st.session_state["calendar"],
        options=calendar_options,
        key="streamlit_calendar",
    )

def settings_page():
    st.title("Settings")
    st.subheader("User Preferences")

    calendar_view = st.selectbox(
        "Preferred Calendar View",
        options=["dayGridMonth", "timeGridWeek", "timeGridDay"],
        index=["dayGridMonth", "timeGridWeek", "timeGridDay"].index(
            st.session_state.get("calendar_view") or "dayGridMonth"
        ),
    )
    notification_preferences = st.text_input(
        "Notification Preferences",
        value=get_config("notification_preferences", "Email, SMS"),
    )
    _SECRETS = "backend/storage/secrets.toml"
    _provider_options = ["OpenAI", "Groq", "Gemini", "Mistral", "Ollama"]
    _saved_provider = get_config("api_provider", "OpenAI", _SECRETS)
    _provider_index = next((i for i, v in enumerate(_provider_options) if v.lower() == _saved_provider.lower()), 0)
    api_provider = st.selectbox("API Provider", options=_provider_options, index=_provider_index)
    ai_model = st.text_input(
        "AI Model",
        value=get_config(f"{api_provider.lower()}_model", f"{api_provider.lower()}-default", _SECRETS),
    )
    api_key = st.text_input("API Key", type="password")

    if st.button("Save Preferences"):
        if api_provider:
            set_config("api_provider", api_provider, "backend/storage/secrets.toml")
        if ai_model:
            set_config(f"{api_provider.lower()}_model", ai_model, "backend/storage/secrets.toml")
        if api_key:
            set_config("api_key", api_key, "backend/storage/secrets.toml")
        st.session_state["calendar_view"] = calendar_view
        set_config("calendar_view", calendar_view)
        set_config("notification_preferences", notification_preferences)
        st.success("Preferences saved successfully!")

    st.divider()
    st.subheader("Google Account")
    connect_button()

    st.divider()
    if st.button("Clear Cache"):
        removed = 0
        for cache_dir in PROJECT_ROOT.rglob("__pycache__"):
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                removed += 1
        st.success(f"Cache cleared — {removed} folder(s) removed.")

def todo_page():
    st.title("Todo List")

    result = subprocess.run(["python", "backend/tools/todo_stuff.py", "--get"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    todos = json.loads(result.stdout or "[]")

    st.divider()

    if not todos:
        st.info("No tasks yet. Add one above.")
    else:
        for i, todo in enumerate(todos):
            col1, col2, col3 = st.columns([3, 5, 1])
            col1.markdown(f"**{todo.get('title', '')}**")
            col2.caption(todo.get("description", ""))
            if col3.button("✕", key=f"del_{i}"):
                subprocess.run(["python", "backend/tools/todo_stuff.py", "--delete", str(i)],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT))
                st.rerun()

def portfolio_page():
    st.title("Calendar AI Assistant — Portfolio")
    st.caption("A smart, multi-interface calendar and productivity manager powered by AI agents.")

    st.divider()

    col1, col2, col3 = st.columns(3)
    col1.metric("AI Providers", "5", help="OpenAI · Groq · Gemini · Mistral · Ollama")
    col2.metric("Interfaces", "2", help="Streamlit web UI + rich CLI")
    col3.metric("Agent Pipeline", "4 agents", help="Intent → Retrieve → Process → Verify")

    st.divider()

    st.subheader("Features")
    feat_col1, feat_col2 = st.columns(2)
    with feat_col1:
        st.markdown("""
**Calendar Management**
- Add, view, and delete events
- Month · week · day grid views
- Google Calendar sync (OAuth 2.0)

**AI Chat**
- Natural language event & task creation
- Multi-provider LLM support
- Runs fully offline with Ollama
""")
    with feat_col2:
        st.markdown("""
**Todo List**
- Add and delete tasks with descriptions
- Persistent JSON storage
- AI-driven task generation from chat

**Google Integration**
- Google Calendar read/write
- Gmail read-only inbox access
- Secure token storage (pickle)
""")

    st.divider()

    st.subheader("Architecture")
    st.markdown("""
```
User (Chat / CLI)
       │
       ▼
 connect_to_ai.py  ──►  Multi-provider LLM  (OpenAI · Groq · Gemini · Mistral · Ollama)
       │
       ▼ JSON action
 ┌─────┴───────────────────────────────────────────────┐
 │  add_event → calendar_events.py                     │
 │  add_todo  → todo_stuff.py                          │
 │  chat      → reply printed / displayed              │
 └─────────────────────────────────────────────────────┘
       │
 Google APIs (optional)
 add_google_oauth.py  ──►  Calendar v3  ·  Gmail v1
```
""")

    st.divider()

    st.subheader("Tech Stack")
    tech_col1, tech_col2, tech_col3 = st.columns(3)
    with tech_col1:
        st.markdown("**Frontend**")
        st.markdown("- Streamlit 1.57\n- streamlit-calendar\n- Rich (CLI)")
    with tech_col2:
        st.markdown("**AI / Agents**")
        st.markdown("- CrewAI 1.1\n- OpenAI SDK\n- Multi-provider routing")
    with tech_col3:
        st.markdown("**Auth / APIs**")
        st.markdown("- google-auth-oauthlib\n- googleapiclient\n- TOML config")

    st.divider()

    google_status_raw = subprocess.run(
        ["python", "backend/auth/add_google_oauth.py", "--status"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    try:
        google_info = json.loads(google_status_raw.stdout.strip() or "{}")
    except json.JSONDecodeError:
        google_info = {}

    st.subheader("Live Google Status")
    if google_info.get("connected"):
        st.success(f"Connected as **{google_info.get('email', 'unknown')}** ({google_info.get('name', '')})")

        if st.button("Load upcoming Google Calendar events"):
            events_raw = subprocess.run(
                ["python", "backend/auth/add_google_oauth.py", "--list-events", "--max", "10"],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            )
            try:
                events = json.loads(events_raw.stdout.strip() or "[]")
                if isinstance(events, list) and events:
                    for ev in events:
                        st.markdown(f"- **{ev['title']}** — {ev['start']}" + (f" @ {ev['location']}" if ev.get('location') else ""))
                elif isinstance(events, dict) and "error" in events:
                    st.error(events["error"])
                else:
                    st.info("No upcoming events.")
            except json.JSONDecodeError:
                st.error("Could not parse events response.")
    else:
        st.info("Google account not connected. Connect via the **Settings** page to see live data.")


pages = [
    st.Page(description_page, title="Description", icon=":material/description:"),
    st.Page(portfolio_page, title="Portfolio", icon=":material/star:"),
    st.Page(calendar_page, title="Calendar", icon=":material/calendar_month:"),
    st.Page(todo_page, title="Todo List", icon=":material/checklist:"),
    st.Page(settings_page, title="Settings", icon=":material/settings:"),
]

current_page = st.navigation(pages, position="top")
current_page.run()

with st.sidebar:
    st.title("Calendar AI Assistant")

    chat_container = st.container(height=400)
    with chat_container:
        if st.session_state["chat_history"]:
            for msg in st.session_state["chat_history"]:
                if msg.startswith("You:"):
                    st.chat_message("user").write(msg[4:].strip())
                else:
                    st.chat_message("assistant").write(msg[4:].strip())
        else:
            st.caption("No messages yet.")

    with st.form("ai_form", clear_on_submit=True):
        user_input = st.text_area("Ask me anything about your calendar:", height=110, max_chars=1000)
        if st.form_submit_button("Send"):
            if user_input.strip():
                st.session_state["chat_history"].append(f"You: {user_input.strip()}")
                response = subprocess.run(
                    ["python", "backend/tools/connect_to_ai.py", "--ask", user_input.strip(), "--provider", get_config("api_provider", "ollama")],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT),
                )
                ai_response = response.stdout.strip()
                st.session_state["chat_history"].append(f"AI: {ai_response}")
                st.rerun()