# Modules for functionality
import os
import streamlit as st
from streamlit_option_menu import option_menu
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from backend.tools.calendar_events import get_calendar_events

description_page = st.Page("Description.py", title="Description", icon=":material/info:")
calendar_page = st.Page("Calendar.py", title="Calendar", icon=":material/chat:")
todo_page = st.Page("Todo.py", title="Todo", icon=":material/list-task:")
settings_page = st.Page("Settings.py", title="Settings", icon=":material/settings:")
pg = st.navigation([description_page, calendar_page, todo_page, settings_page])
pg.run()

if not st.session_state.get("initialized", False):
    st.session_state["initialized"] = True
    st.session_state["calendar"] = get_calendar_events()

st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")
st.title("Description of this project")

with open("README.md", "r") as file:
    description = file.read()
st.markdown(description)