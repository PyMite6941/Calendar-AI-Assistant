# Modules for functionality
import streamlit as st
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from backend.tools.calendar_events import get_calendar_events

if not st.session_state.get("initialized", False):
    st.session_state["initialized"] = True
    st.session_state["calendar"] = get_calendar_events()