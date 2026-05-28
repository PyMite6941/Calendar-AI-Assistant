# Modules for functionality
import streamlit as st

from backend.tools.calendar_events import get_calendar_events

if not st.session_state.get("initialized", False):
    st.session_state["initialized"] = True
    st.session_state["calendar"] = get_calendar_events()

st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")
st.title("Description of this project")

with open("README.md", "r") as file:
    description = file.read()
st.markdown(description)