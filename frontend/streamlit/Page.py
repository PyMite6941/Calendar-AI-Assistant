import json
import shutil
import subprocess
import sys
from pathlib import Path

import streamlit as st
from streamlit_calendar import calendar

_PY = sys.executable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.auth.add_google_oauth import connect_button, get_creds

_SECRETS = "backend/storage/secrets.toml"
_PRIORITY_COLORS = {"high": "🔴", "medium": "🟡", "low": "🟢"}
_STATUS_COLORS   = {"pending": "⬜", "in-progress": "🔵", "done": "✅"}


# ── helpers ───────────────────────────────────────────────────────────────────

def _run(*cmd):
    return subprocess.run(list(cmd), capture_output=True, text=True, cwd=str(PROJECT_ROOT))

def get_calendar_events():
    try:
        return json.loads(_run(_PY, "backend/tools/calendar_events.py", "--get").stdout or "[]")
    except json.JSONDecodeError:
        return []

def get_config(key, default=None, path=None):
    cmd = [_PY, "backend/tools/config_editing.py", "--key", key, "--default", str(default)]
    if path:
        cmd += ["--path", path]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT)).stdout.strip()

def set_config(key, value, path="backend/storage/configs.toml"):
    _run(_PY, "backend/tools/config_editing.py", "--key", key, "--set", str(value), "--path", path)

def get_todos():
    try:
        return json.loads(_run(_PY, "backend/tools/todo_stuff.py", "--get").stdout or "[]")
    except json.JSONDecodeError:
        return []


# ── page setup ────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Calendar AI Assistant", page_icon=":calendar:", layout="centered")
get_creds()

if not st.session_state.get("initialized"):
    st.session_state["initialized"]    = True
    st.session_state["calendar_view"]  = get_config("calendar_view", "dayGridMonth")
    st.session_state["chat_history"]   = []


# ── dialogs ───────────────────────────────────────────────────────────────────

@st.dialog("Todo Details")
def _todo_detail_dialog(index: int, todo: dict):
    priority = todo.get("priority", "medium")
    status   = todo.get("status", "pending")
    st.markdown(f"## {todo.get('title', '')}")
    st.caption(f"{_PRIORITY_COLORS.get(priority, '')} {priority.capitalize()} priority  ·  {_STATUS_COLORS.get(status, '')} {status.capitalize()}")

    due = todo.get("due_date", "")
    if due:
        st.markdown(f"**Due:** {due}")

    if todo.get("description"):
        st.markdown(f"**Description:** {todo['description']}")

    tags = todo.get("tags", [])
    if tags:
        st.markdown("**Tags:** " + "  ".join(f"`{t}`" for t in tags))

    if todo.get("notes"):
        st.markdown("**Notes:**")
        st.info(todo["notes"])

    st.divider()
    st.subheader("Edit")

    new_title    = st.text_input("Title",       value=todo.get("title", ""))
    new_desc     = st.text_input("Description", value=todo.get("description", ""))
    col1, col2   = st.columns(2)
    new_priority = col1.selectbox("Priority", ["low", "medium", "high"],
                                  index=["low","medium","high"].index(priority))
    new_status   = col2.selectbox("Status", ["pending", "in-progress", "done"],
                                  index=["pending","in-progress","done"].index(status))
    new_due      = st.text_input("Due date (YYYY-MM-DD)", value=todo.get("due_date", ""))
    new_tags_raw = st.text_input("Tags (comma-separated)", value=", ".join(tags))
    new_notes    = st.text_area("Notes", value=todo.get("notes", ""), height=100)

    col_save, col_del, _ = st.columns([2, 2, 4])
    if col_save.button("Save", type="primary", use_container_width=True):
        patch = {
            "title":       new_title.strip(),
            "description": new_desc.strip(),
            "priority":    new_priority,
            "status":      new_status,
            "due_date":    new_due.strip(),
            "tags":        [t.strip() for t in new_tags_raw.split(",") if t.strip()],
            "notes":       new_notes.strip(),
        }
        _run(_PY, "backend/tools/todo_stuff.py", "--update", str(index), "--json", json.dumps(patch))
        st.rerun()
    if col_del.button("Delete", type="secondary", use_container_width=True):
        _run(_PY, "backend/tools/todo_stuff.py", "--delete", str(index))
        st.rerun()


@st.dialog("Event Details")
def _event_detail_dialog(index: int, event: dict):
    st.markdown(f"## {event.get('title', '')}")

    col1, col2 = st.columns(2)
    col1.markdown(f"**Start:** {event.get('start', '')}")
    col2.markdown(f"**End:**   {event.get('end', '')}")

    if event.get("location"):
        st.markdown(f"**Location:** {event['location']}")
    if event.get("description"):
        st.markdown(f"**Description:** {event['description']}")
    if event.get("recurrence", "none") != "none":
        st.markdown(f"**Recurrence:** {event['recurrence'].capitalize()}")
    if event.get("reminder"):
        st.markdown(f"**Reminder:** {event['reminder']} min before")

    st.divider()
    st.subheader("Edit")

    new_title  = st.text_input("Title",    value=event.get("title", ""))
    col_s, col_e = st.columns(2)
    new_start  = col_s.text_input("Start (YYYY-MM-DDTHH:MM:SS)", value=event.get("start", ""))
    new_end    = col_e.text_input("End   (YYYY-MM-DDTHH:MM:SS)", value=event.get("end",   ""))
    new_desc   = st.text_input("Description", value=event.get("description", ""))
    new_loc    = st.text_input("Location",    value=event.get("location", ""))
    col_r, col_rec = st.columns(2)
    new_reminder   = col_r.number_input("Reminder (min)", min_value=0, value=int(event.get("reminder") or 0))
    _rec_opts      = ["none", "daily", "weekly", "monthly"]
    _rec_idx       = _rec_opts.index(event.get("recurrence", "none")) if event.get("recurrence", "none") in _rec_opts else 0
    new_recurrence = col_rec.selectbox("Recurrence", _rec_opts, index=_rec_idx)

    col_save, col_del, _ = st.columns([2, 2, 4])
    if col_save.button("Save", type="primary", use_container_width=True):
        patch = {
            "title":       new_title.strip(),
            "start":       new_start.strip(),
            "end":         new_end.strip(),
            "description": new_desc.strip(),
            "location":    new_loc.strip(),
            "reminder":    int(new_reminder),
            "recurrence":  new_recurrence,
        }
        _run(_PY, "backend/tools/calendar_events.py", "--update", str(index), "--json", json.dumps(patch))
        st.rerun()
    if col_del.button("Delete", type="secondary", use_container_width=True):
        _run(_PY, "backend/tools/calendar_events.py", "--delete", str(index))
        st.rerun()


# ── pages ─────────────────────────────────────────────────────────────────────

def description_page():
    st.title("Description of this project")
    st.markdown("## Inspiration")
    st.write("Mackenzie actually recommended this project for us to do and it was so fun that we both got carried away in our work.")
    st.markdown("## What it does")
    st.write("This project uses Python as the main language and the module Streamlit for the Web UI and the module CrewAI for the scraping of Calendar materials such as Google Mail and Google Calendar.")
    st.markdown("## How we built it")
    st.write("This project had a few major parts, the AI component, the tools, and the frontend. These seem basic however even with the level of abstraction that Streamlit and Rich give still make everything semi-complicated. The AI component uses the user's API key or Ollama to connect the sidebar directly to the AI brain and the CrewAI agents for their thinking. The tools use argparse to process terminal commands for the tools programs and subprocess for the tool usage. The frontend is also quite complex between the two files, the run.py is meant to run the selected files for the terminal view and the Streamlit view while also providing a place to update the programs.")
    st.markdown("## Challenges we ran into")
    st.write("A big challenge that we had was communication since this was Mackenzie's first major programming project and this was one of Matt's few collabration programming projects.")
    st.markdown("## Accomplishments that we're proud of")
    st.write("Something we are proud of is that Maceknzie learned some python for the first time and we both developed our ability to use CrewAI a lot.")
    st.markdown("## What we learned")
    st.write("We learned how to best configure configuration files and also how to use APIs more effectively in the use of AI projects including modules like OpenAI and CrewAI.")
    st.markdown("## What's next for Calendar AI Tool")
    st.write("I (Matt) will continue to maintain this repo and improve it where necessary while Mackenzie may go a different direction with programming.")


def calendar_page():
    st.title("Your Calendar, AI Managed")

    events = get_calendar_events()
    # Build a title→index map so we can open the right dialog on click
    title_to_index = {e.get("title", ""): i for i, e in enumerate(events)}

    calendar_options = {
        "initialView": st.session_state.get("calendar_view", "dayGridMonth"),
        "headerToolbar": {
            "left":   "prev,next today",
            "center": "title",
            "right":  "dayGridMonth,timeGridWeek,timeGridDay",
        },
        "selectable": True,
        "eventColor": "#7c3aed",
    }

    # Map events to streamlit-calendar format, keep index for lookup
    cal_events = []
    for i, e in enumerate(events):
        cal_events.append({
            "title":           e.get("title", ""),
            "start":           e.get("start", ""),
            "end":             e.get("end", "") or e.get("start", ""),
            "backgroundColor": e.get("color") or "#7c3aed",
            "extendedProps":   {"index": i},
        })

    state = calendar(events=cal_events, options=calendar_options, key="streamlit_calendar")

    if state and state.get("eventClick"):
        clicked_title = state["eventClick"]["event"].get("title", "")
        idx = title_to_index.get(clicked_title)
        if idx is not None:
            _event_detail_dialog(idx, events[idx])


def todo_page():
    st.title("Todo List")
    st.caption("Items are added by the AI assistant in the sidebar chat. Click any item to view details or edit.")

    todos = get_todos()

    if not todos:
        st.info("No todos yet — ask the AI to add one.")
        return

    # Filter controls
    col_status, col_priority, _ = st.columns([2, 2, 4])
    filter_status   = col_status.selectbox("Filter by status",   ["all", "pending", "in-progress", "done"], label_visibility="collapsed")
    filter_priority = col_priority.selectbox("Filter by priority", ["all", "high", "medium", "low"], label_visibility="collapsed")

    shown = [
        (i, t) for i, t in enumerate(todos)
        if (filter_status   == "all" or t.get("status",   "pending") == filter_status)
        and (filter_priority == "all" or t.get("priority", "medium")  == filter_priority)
    ]

    if not shown:
        st.info("No items match the current filter.")
        return

    st.divider()
    for i, todo in shown:
        priority = todo.get("priority", "medium")
        status   = todo.get("status",   "pending")
        due      = todo.get("due_date", "")

        col_main, col_btn = st.columns([9, 1])
        with col_main:
            badges = f"{_PRIORITY_COLORS.get(priority,'')} {_STATUS_COLORS.get(status,'')} "
            due_str = f"  ·  due {due}" if due else ""
            st.markdown(f"{badges} **{todo.get('title','')}**{due_str}")
            if todo.get("description"):
                st.caption(todo["description"])
        if col_btn.button("⋯", key=f"detail_{i}", help="View / edit"):
            _todo_detail_dialog(i, todo)


def settings_page():
    st.title("Settings")
    st.subheader("User Preferences")

    user_name = st.text_input(
        "Your name",
        value=get_config("user_name", ""),
        placeholder="e.g. Matt",
        help="The AI will address you by name and personalise responses.",
    )
    timezone = st.text_input(
        "Timezone",
        value=get_config("timezone", ""),
        placeholder="e.g. Asia/Bangkok",
        help="IANA timezone name. Used so the AI knows your local time when resolving dates.",
    )
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
    _provider_options = ["OpenAI", "Groq", "Gemini", "Mistral", "Ollama"]
    _saved_provider   = get_config("api_provider", "OpenAI", _SECRETS)
    _provider_index   = next((i for i, v in enumerate(_provider_options) if v.lower() == _saved_provider.lower()), 0)
    api_provider  = st.selectbox("API Provider", options=_provider_options, index=_provider_index)
    ai_model      = st.text_input(
        "AI Model",
        value=get_config(f"{api_provider.lower()}_model", f"{api_provider.lower()}-default", _SECRETS),
    )
    api_key = st.text_input("API Key", type="password")

    if st.button("Save Preferences"):
        set_config("api_provider",               api_provider,    _SECRETS)
        set_config(f"{api_provider.lower()}_model", ai_model,     _SECRETS)
        if api_key:
            set_config("api_key", api_key, _SECRETS)
        st.session_state["calendar_view"] = calendar_view
        set_config("user_name",                  user_name.strip())
        set_config("timezone",                   timezone.strip())
        set_config("calendar_view",              calendar_view)
        set_config("notification_preferences",   notification_preferences)
        st.success("Preferences saved.")

    st.divider()
    st.subheader("Google Account")
    connect_button()

    st.divider()
    if st.button("Clear Cache"):
        removed = 0
        for d in PROJECT_ROOT.rglob("__pycache__"):
            if d.exists():
                shutil.rmtree(d)
                removed += 1
        st.success(f"Cache cleared — {removed} folder(s) removed.")


_PLAN_TRIGGERS = {
    "plan my day", "plan my schedule", "daily plan", "optimize my schedule",
    "optimise my schedule", "schedule my day", "time block my day", "plan today",
    "organize my day", "organise my day",
}

def _is_planning_request(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _PLAN_TRIGGERS)


def planner_page():
    st.title("Daily Planner")
    st.caption("The AI reads your calendar and todos to build an optimised, time-blocked plan for today.")

    plan_path = PROJECT_ROOT / "backend/storage/daily_plan.json"
    plan_data = {}
    if plan_path.exists():
        try:
            plan_data = json.loads(plan_path.read_text())
        except json.JSONDecodeError:
            pass

    col_info, col_btn = st.columns([5, 1])
    if plan_data:
        gen_at     = plan_data.get("generated_at", "")[:19].replace("T", " ")
        plan_date  = plan_data.get("plan_date", "")
        col_info.caption(f"Generated: {gen_at}  ·  For: {plan_date}")
    else:
        col_info.info("No plan yet — ask the AI to plan your day, or click Generate.")

    if col_btn.button("Generate", type="primary"):
        with st.spinner("Building your plan…"):
            res = _run(_PY, "backend/agents/planner_crew.py")
        if res.returncode == 0:
            st.rerun()
        else:
            st.error(f"Planner failed: {(res.stderr or res.stdout)[:400]}")
        return

    if plan_data.get("plan_text"):
        st.divider()
        st.markdown(plan_data["plan_text"])


def portfolio_page():
    st.title("Calendar AI Assistant — Portfolio")
    st.caption("A smart, multi-interface calendar and productivity manager powered by AI agents.")

    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("AI Providers",   "5",        help="OpenAI · Groq · Gemini · Mistral · Ollama")
    col2.metric("Interfaces",     "2",        help="Streamlit web UI + rich CLI")
    col3.metric("Agent Pipeline", "4 agents", help="Intent → Retrieve → Process → Verify")

    st.divider()
    st.subheader("Features")
    feat1, feat2 = st.columns(2)
    with feat1:
        st.markdown("""
**Calendar Management**
- Add, view, edit, delete events
- Rich event fields: location, reminders, recurrence
- Month · week · day grid views
- Google Calendar sync (OAuth 2.0)

**AI Chat**
- Natural language event & task creation
- Multi-provider LLM support
- Runs fully offline with Ollama
""")
    with feat2:
        st.markdown("""
**Todo List**
- Priority, status, due date, tags, notes
- Filter by status or priority
- Click-to-edit popup details
- AI-driven task generation from chat

**Google Integration**
- Google Calendar read/write
- Gmail read-only inbox access
- Secure token storage (pickle)
""")

    st.divider()
    st.subheader("Architecture")
    st.code("""\
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
""", language="text")

    st.divider()
    st.subheader("Tech Stack")
    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown("**Frontend**\n- Streamlit 1.57\n- streamlit-calendar\n- Rich (CLI)")
    with t2:
        st.markdown("**AI / Agents**\n- CrewAI 1.14\n- OpenAI SDK\n- Multi-provider routing")
    with t3:
        st.markdown("**Auth / APIs**\n- google-auth-oauthlib\n- googleapiclient\n- TOML config")

    st.divider()
    st.subheader("Live Google Status")
    try:
        google_info = json.loads(_run(_PY, "backend/auth/add_google_oauth.py", "--status").stdout.strip() or "{}")
    except json.JSONDecodeError:
        google_info = {}

    if google_info.get("connected"):
        st.success(f"Connected as **{google_info.get('email','unknown')}** ({google_info.get('name','')})")
        if st.button("Load upcoming Google Calendar events"):
            try:
                evts = json.loads(_run(_PY, "backend/auth/add_google_oauth.py", "--list-events", "--max", "10").stdout.strip() or "[]")
                if isinstance(evts, list) and evts:
                    for ev in evts:
                        st.markdown(f"- **{ev['title']}** — {ev['start']}" + (f" @ {ev['location']}" if ev.get("location") else ""))
                elif isinstance(evts, dict) and "error" in evts:
                    st.error(evts["error"])
                else:
                    st.info("No upcoming events.")
            except json.JSONDecodeError:
                st.error("Could not parse events response.")
    else:
        st.info("Google account not connected. Connect via the **Settings** page.")


# ── navigation ────────────────────────────────────────────────────────────────

pages = [
    st.Page(description_page, title="Description",  icon=":material/description:"),
    st.Page(portfolio_page,   title="Portfolio",    icon=":material/star:"),
    st.Page(calendar_page,    title="Calendar",     icon=":material/calendar_month:"),
    st.Page(todo_page,        title="Todo List",    icon=":material/checklist:"),
    st.Page(planner_page,     title="Daily Planner",icon=":material/today:"),
    st.Page(settings_page,    title="Settings",     icon=":material/settings:"),
]

current_page = st.navigation(pages, position="top")
current_page.run()

# ── sidebar AI chat ───────────────────────────────────────────────────────────

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
            st.caption("Ask me to add events or tasks.")

    with st.form("ai_form", clear_on_submit=True):
        user_input = st.text_area("Ask me anything about your calendar:", height=110, max_chars=1000)
        if st.form_submit_button("Send"):
            if user_input.strip():
                st.session_state["chat_history"].append(f"You: {user_input.strip()}")
                if _is_planning_request(user_input):
                    with st.spinner("Building your plan…"):
                        resp = _run(_PY, "backend/agents/planner_crew.py")
                    if resp.returncode == 0:
                        ai_reply = resp.stdout.strip() or "Plan generated — check the Daily Planner page to view it."
                    else:
                        ai_reply = f"Failed to generate plan: {(resp.stderr or resp.stdout)[:300]}"
                else:
                    provider = get_config("api_provider", "ollama", _SECRETS)
                    resp = _run(_PY, "backend/tools/connect_to_ai.py", "--ask", user_input.strip(), "--provider", provider)
                    ai_reply = resp.stdout.strip()
                st.session_state["chat_history"].append(f"AI: {ai_reply}")
                st.rerun()
