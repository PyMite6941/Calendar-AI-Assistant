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

from backend.auth.add_google_oauth import connect_button, get_creds, disconnect

def get_calendar_events():
    result = subprocess.run(["python", "backend/tools/calendar_events.py", "--get"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    return result.stdout

def get_config(key, default=None):
    result = subprocess.run(["python", "backend/tools/config_editing.py", "--key", key, "--default", str(default)], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    return result.stdout.strip()

def set_config(key, value, path="backend/storage/configs.toml"):
    subprocess.run(["python", "backend/tools/config_editing.py", "--key", key, "--set", str(value), "--path", path], capture_output=True, text=True, cwd=str(PROJECT_ROOT))

def get_todo_list():
    result = subprocess.run(["python", "backend/tools/todo_list.py", "--get"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    return result.stdout

if not st.session_state.get("initialized", False):
    st.session_state["initialized"] = True
    st.session_state["calendar"] = get_calendar_events()
    st.session_state["calendar_view"] = get_config("calendar_view", "dayGridMonth")
    st.session_state["todo_list"] = get_todo_list()
    st.session_state["chat_history"] = []

def description_page():
    st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")
    st.title("Description of this project")
    readme = PROJECT_ROOT / "README.md"
    st.markdown(readme.read_text() if readme.exists() else "_No description yet._")

def calendar_page():
    st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")
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
    st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")
    st.title("Settings")
    st.subheader("User Preferences")

    calendar_view = st.selectbox(
        "Preferred Calendar View",
        options=["dayGridMonth", "timeGridWeek", "timeGridDay"],
        index=["dayGridMonth", "timeGridWeek", "timeGridDay"].index(
            st.session_state.get("calendar_view", "dayGridMonth")
        ),
    )
    notification_preferences = st.text_input("Notification Preferences", value="Email, SMS")
    api_provider = st.selectbox("API Provider", options=["OpenAI", "Groq", "Gemini", "Mistral", "Ollama"], index=["OpenAI", "Groq", "Gemini", "Mistral", "Ollama"].index(get_config("api_provider", "OpenAI")))
    ai_model = st.text_input("AI Model", value=get_config(f"{api_provider.lower()}_model", f"{api_provider}-3.5-turbo"))
    api_key = st.text_input("API Key", type="password")

    if st.button("Save Preferences"):
        if api_provider:
            set_config("api_provider", api_provider, "backend/storage/secrets.toml")
        if ai_model:
            set_config(f"{api_provider}_model", ai_model, "backend/storage/secrets.toml")
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
    st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")
    st.title("Todo List")

    result = subprocess.run(["python", "backend/tools/todo_stuff.py", "--get"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    todos = json.loads(result.stdout or "[]")

    with st.form("add_todo_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 3])
        title = col1.text_input("Title")
        desc  = col2.text_input("Description")
        if st.form_submit_button("Add Task") and title:
            subprocess.run(["python", "backend/tools/todo_stuff.py", "--add", title, desc],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT))
            st.rerun()

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
    st.session_state["todo_list"] = get_todo_list()
    todos = st.session_state["todo_list"]
    if todos:
        for idx, todo in enumerate(todos):
            st.markdown(f"**{idx+1}. {todo['title']}**: {todo['description']}")
            if st.button(f"Delete Task {idx+1}", key=f"delete_{idx}"):
                subprocess.run(["python", "backend/tools/todo_stuff.py", "--delete", str(idx)], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
                st.session_state["todo_list"] = get_todo_list()
                st.experimental_rerun()
    else:
        st.info("Your todo list is empty. Add some tasks to get started!")

pages = [
    st.Page(description_page, title="Description", icon=":material/description:"),
    st.Page(calendar_page, title="Calendar", icon=":material/calendar_month:"),
    st.Page(todo_page, title="Todo List", icon=":material/checklist:"),
    st.Page(settings_page, title="Settings", icon=":material/settings:"),
]

current_page = st.navigation(pages, position="top")
current_page.run()

with st.sidebar:
    st.write(st.session_state["chat_history"] if st.session_state["chat_history"] else "")
    st.title("Talk to your Calendar AI Assistant")
    with st.form("ai_form"):
        user_input = st.text_input("Ask me anything about your calendar:")
        if st.form_submit_button("Submit"):
            if user_input:
                st.session_state["chat_history"].append(f"You: {user_input}")
                response = subprocess.run(["python", "backend/tools/connect_to_ai.py", "--ask", user_input, "--model", get_config("api_provider", "openai")], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
                ai_response = response.stdout.strip()
                st.session_state["chat_history"].append(f"AI: {ai_response}")