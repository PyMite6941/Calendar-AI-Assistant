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
    result = subprocess.run(["python", "backend/tools/access_configs.py", "--key", key, "--default", str(default)], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    return result.stdout.strip()

def set_config(key, value):
    subprocess.run(["python", "backend/tools/access_configs.py", "--key", key, "--set", str(value)], capture_output=True, text=True, cwd=str(PROJECT_ROOT))

if not st.session_state.get("initialized", False):
    st.session_state["initialized"] = True
    st.session_state["calendar"] = get_calendar_events()
    st.session_state["calendar_view"] = get_config("calendar_view", "dayGridMonth")
    st.session_state["chat_history"] = []

def description_page():
    st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")
    st.title("Description of this project")

    with open("README.md", "r") as file:
        description = file.read()
    st.markdown(description)

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

    state = calendar(
        events=st.session_state["calendar"],
        options=calendar_options,
        key="streamlit_calendar",
    )

def settings_page():
    st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")
    st.title("Settings")
    st.subheader("User Preferences")
    calendar_view = st.multiselect("Preferred Calendar View", options=["dayGridMonth", "timeGridWeek", "timeGridDay"], default=["dayGridMonth"])
    notification_preferences = st.text_input("Notification Preferences", value="Email, SMS")
    api_provider = st.text_input("API Provider", value="OpenAI")
    api_key = st.text_input("API Key", type="password")
    if st.button("Save Preferences"):
        st.session_state["calendar_view"] = calendar_view
        set_config("calendar_view", calendar_view)
        set_config("notification_preferences", notification_preferences)
        st.success("Preferences saved successfully!")
    if st.button("Clear Cache"):
        subprocess.run(["python", "backend/tools/remove_cache.py"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        st.success("Cache cleared successfully!")

def todo_page():
    st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")
    st.title("Todo List")
    st.subheader("Your Tasks")
    st.text_input("Add a new task", key="new_task")
    if st.button("Add Task"):
        new_task = st.session_state["new_task"]
        if new_task:
            subprocess.run(["python", "backend/tools/todo_stuff.py", "--add", new_task, ""], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
            st.session_state["chat_history"].append(f"Task added: {new_task}")
            st.success(f"Task '{new_task}' added to your todo list!")

pages = [
    st.Page(description_page, title="Description",icon=":material/description:"),
    st.Page(calendar_page, title="Calendar", icon=":material/calendar_month:"),
    st.Page(todo_page, title="Todo List", icon=":material/checklist:"),
    st.Page(settings_page, title="Settings", icon=":material/settings:"),
]

current_page = st.navigation(pages,position="top")
current_page.run()

with st.sidebar:
    st.write(st.session_state["chat_history"] if st.session_state["chat_history"] else "")
    st.title("Talk to your Calendar AI Assistant")
    with st.form("ai_form"):
        user_input = st.text_input("Ask me anything about your calendar:")
        submit_button = st.form_submit_button("Submit")
    st.divider()
    connect_button()