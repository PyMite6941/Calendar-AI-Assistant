# Modules for functionality
import streamlit as st
from streamlit_calendar import calendar

from backend.tools.calendar_events import get_calendar_events

if not st.session_state.get("initialized", False):
    st.session_state["initialized"] = True
    st.session_state["calendar"] = get_calendar_events()

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