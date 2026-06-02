# Modules for functionality
import streamlit as st
from streamlit_calendar import calendar
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from backend.tools.calendar_events import get_calendar_events

if not st.session_state.get("initialized", False):
    st.session_state["initialized"] = True
    st.session_state["calendar"] = get_calendar_events()

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
        "initialView": "dayGridMonth",
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

    with st.sidebar:
        st.header("Talk to an AI Assistant")
        with st.form("ai_form"):
            user_input = st.text_input("Ask me anything about your calendar:")
            submit_button = st.form_submit_button("Submit")

def settings_page():
    st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")
    st.title("Settings")

    st.subheader("User Preferences")
    st.text_input("Preferred Calendar View", value="Month")
    st.text_input("Notification Preferences", value="Email, SMS")

def todo_page():
    st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")
    st.title("Todo List")

    st.subheader("Your Tasks")
    st.text_input("Add a new task", key="new_task")
    if st.button("Add Task"):
        new_task = st.session_state["new_task"]
        if new_task:
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
    st.title("Talk to your Calendar AI Assistant")
    with st.form("ai_form"):
        user_input = st.text_input("Ask me anything about your calendar:")
        submit_button = st.form_submit_button("Submit")