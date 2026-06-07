import json
import subprocess
import sys
import tomllib
import urllib.request
from pathlib import Path

from crewai import Agent, LLM
from crewai.tools import tool

_ROOT = Path(__file__).resolve().parents[2]


# ── LLM factory ───────────────────────────────────────────────────────────────

def _get_ollama_model(preferred: str) -> str:
    """Return the preferred model if available, else the first listed model, else preferred."""
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            models = [m["name"] for m in json.loads(r.read()).get("models", [])]
        if not models:
            return preferred
        if preferred in models:
            return preferred
        for m in models:
            if m.startswith(preferred.split(":")[0]):
                return m
        return models[0]
    except Exception:
        return preferred


def _build_llm() -> LLM:
    """Build a crewai.LLM from the project's secrets.toml provider settings."""
    secrets_path = _ROOT / "backend/storage/secrets.toml"
    try:
        with open(secrets_path, "rb") as f:
            secrets = tomllib.load(f)
    except FileNotFoundError:
        secrets = {}

    provider = (secrets.get("api_provider") or "ollama").lower()
    api_key  = secrets.get("api_key") or ""

    _default_models = {
        "openai":  "gpt-4o-mini",
        "groq":    "llama-3.1-8b-instant",
        "gemini":  "gemini-2.0-flash",
        "mistral": "mistral-small-latest",
        "ollama":  "llama3.2",
    }
    model = secrets.get(f"{provider}_model") or _default_models.get(provider, "llama3.2")

    if provider == "ollama":
        model = _get_ollama_model(model)
        return LLM(model=f"ollama/{model}", base_url="http://localhost:11434")
    elif provider == "groq":
        return LLM(model=f"groq/{model}", api_key=api_key)
    elif provider == "gemini":
        return LLM(model=f"gemini/{model}", api_key=api_key)
    elif provider == "mistral":
        return LLM(model=f"mistral/{model}", api_key=api_key)
    else:
        return LLM(model=model, api_key=api_key)


_llm = _build_llm()


# ── local tools ───────────────────────────────────────────────────────────────

@tool("get_calendar_events")
def get_calendar_events() -> str:
    """Return all local calendar events as a JSON array."""
    result = subprocess.run(
        [sys.executable, "backend/tools/calendar_events.py", "--get"],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or "[]"


@tool("add_calendar_event")
def add_calendar_event(title: str, start: str, end: str,
                       description: str = "", location: str = "",
                       reminder: int = 0, recurrence: str = "none") -> str:
    """Add a local calendar event. start/end: ISO 8601 (YYYY-MM-DDTHH:MM:SS).
    recurrence: none | daily | weekly | monthly. Returns JSON confirmation."""
    result = subprocess.run(
        [sys.executable, "backend/tools/calendar_events.py", "--add",
         title, start, end, description, location, "", str(reminder), recurrence],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("update_calendar_event")
def update_calendar_event(index: int, patch_json: str) -> str:
    """Update a local calendar event by index. patch_json: JSON object of fields to change.
    Returns JSON confirmation or error."""
    result = subprocess.run(
        [sys.executable, "backend/tools/calendar_events.py", "--update", str(index), "--json", patch_json],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("delete_calendar_event")
def delete_calendar_event(index: int) -> str:
    """Delete a local calendar event by its 0-based index. Returns JSON confirmation or error."""
    result = subprocess.run(
        [sys.executable, "backend/tools/calendar_events.py", "--delete", str(index)],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("get_todos")
def get_todos() -> str:
    """Return all todo items as a JSON array."""
    result = subprocess.run(
        [sys.executable, "backend/tools/todo_stuff.py", "--get"],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or "[]"


@tool("add_todo")
def add_todo(title: str, description: str = "", priority: str = "medium",
             due_date: str = "", status: str = "pending", notes: str = "") -> str:
    """Add a todo item. priority: low | medium | high. status: pending | in-progress | done.
    Returns JSON confirmation."""
    result = subprocess.run(
        [sys.executable, "backend/tools/todo_stuff.py", "--add",
         title, description, priority, due_date, status, "[]", notes],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("update_todo")
def update_todo(index: int, patch_json: str) -> str:
    """Update a todo item by index. patch_json: JSON object of fields to change.
    Returns JSON confirmation or error."""
    result = subprocess.run(
        [sys.executable, "backend/tools/todo_stuff.py", "--update", str(index), "--json", patch_json],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("delete_todo")
def delete_todo(index: int) -> str:
    """Delete a todo item by its 0-based index. Returns JSON confirmation or error."""
    result = subprocess.run(
        [sys.executable, "backend/tools/todo_stuff.py", "--delete", str(index)],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("get_config")
def get_config(key: str, default: str = "") -> str:
    """Read a user config value by key (e.g. user_name, timezone, calendar_view)."""
    result = subprocess.run(
        [sys.executable, "backend/tools/config_editing.py", "--key", key, "--default", default],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip()


# ── Google tools ──────────────────────────────────────────────────────────────

@tool("get_google_calendar_events")
def get_google_calendar_events() -> str:
    """Return upcoming Google Calendar events as a JSON array (includes 'id' field for each event).
    Returns [] if Google is not connected. Use the 'id' field when calling update or delete."""
    result = subprocess.run(
        [sys.executable, "backend/auth/add_google_oauth.py", "--list-events"],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    if result.returncode != 0:
        return "[]"
    return result.stdout.strip() or "[]"


@tool("add_google_calendar_event")
def add_google_calendar_event(title: str, start: str, end: str,
                               description: str = "", location: str = "") -> str:
    """Add an event to Google Calendar. start/end: ISO 8601 (YYYY-MM-DDTHH:MM:SS).
    Returns JSON with 'ok' and the new event 'id', or an error message if not connected."""
    event_json = json.dumps({
        "title": title, "start": start, "end": end,
        "description": description, "location": location,
    })
    result = subprocess.run(
        [sys.executable, "backend/auth/add_google_oauth.py", "--add-event", event_json],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("update_google_calendar_event")
def update_google_calendar_event(event_id: str, patch_json: str) -> str:
    """Update a Google Calendar event by its event ID (from get_google_calendar_events).
    patch_json: JSON object of fields to change (title, start, end, description, location).
    Returns JSON confirmation or error."""
    result = subprocess.run(
        [sys.executable, "backend/auth/add_google_oauth.py", "--update-event", event_id, patch_json],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("delete_google_calendar_event")
def delete_google_calendar_event(event_id: str) -> str:
    """Delete a Google Calendar event by its event ID (from get_google_calendar_events).
    Returns JSON confirmation or error."""
    result = subprocess.run(
        [sys.executable, "backend/auth/add_google_oauth.py", "--delete-event", event_id],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("get_gmail_messages")
def get_gmail_messages() -> str:
    """Return recent Gmail inbox messages as a JSON array (subject, from, date, snippet).
    Returns [] if Google is not connected."""
    result = subprocess.run(
        [sys.executable, "backend/auth/add_google_oauth.py", "--list-messages"],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    if result.returncode != 0:
        return "[]"
    return result.stdout.strip() or "[]"


# ── agents ────────────────────────────────────────────────────────────────────

intent_analyzer = Agent(
    role="Request Intent Analyzer",
    goal=(
        "Parse the user's message and produce a precise, structured breakdown of their intent, "
        "extracted entities, and resolved dates that downstream agents can act on without ambiguity."
    ),
    backstory=(
        "You are a seasoned natural-language parser who has processed thousands of calendar and "
        "productivity requests. You never assume — you extract. If a date is relative ('next Friday', "
        "'in four days', 'end of the week'), you resolve it to an absolute date using the timezone "
        "provided in the task context. If a title is missing, you infer the best one from context. "
        "If the intent is ambiguous, you pick the most likely interpretation and state your assumption. "
        "Your output is so structured and complete that downstream agents never need to re-read the original message."
    ),
    llm=_llm,
    tools=[get_config],
)

data_agent = Agent(
    role="Schedule Data Retriever",
    goal=(
        "Fetch exactly the calendar events and todo items that are directly relevant to the analysed "
        "request — no more, no less — and identify the correct index of any item that needs updating or deleting."
    ),
    backstory=(
        "You are a precise data librarian for the user's schedule. You retrieve from both local storage "
        "and Google Calendar when available. When asked about upcoming events, pull from both sources. "
        "When asked to update a local item, find the right one by reading the full list and matching by title — "
        "never guess an index. For Google Calendar items, use the 'id' field returned by get_google_calendar_events. "
        "If nothing relevant exists, report that clearly so the processor can act accordingly."
    ),
    llm=_llm,
    tools=[get_calendar_events, get_todos, get_config, get_google_calendar_events, get_gmail_messages],
)

processing_agent = Agent(
    role="Schedule Processor",
    goal=(
        "Execute the correct write action (add, update, or delete) or compose a clear answer, "
        "using only the analysed intent and retrieved data. Always use absolute ISO dates — never relative ones."
    ),
    backstory=(
        "You are a decisive productivity assistant who takes action. When the intent is clear and the "
        "data is ready, you act: you call the right tool with the right parameters and confirm success. "
        "For add actions, fill in all available fields inferred from the user's message. "
        "For updates, build a precise patch JSON containing only the changed fields. "
        "Write to local storage by default. If the user explicitly mentions Google Calendar or if the "
        "event originated from Google (has an 'id' field), use the Google Calendar tools instead. "
        "Check tool output for 'ok: true' to confirm success — if 'ok' is false, report the error. "
        "For questions, answer in plain, friendly language using the retrieved data."
    ),
    llm=_llm,
    tools=[
        get_calendar_events, add_calendar_event, update_calendar_event, delete_calendar_event,
        get_todos, add_todo, update_todo, delete_todo,
        get_google_calendar_events, add_google_calendar_event,
        update_google_calendar_event, delete_google_calendar_event,
    ],
)

verification_agent = Agent(
    role="Response Verifier and Formatter",
    goal=(
        "Ensure the processor's output is correct and complete, then produce a clean, "
        "friendly final message that is ready to show directly to the user."
    ),
    backstory=(
        "You are the last line of defence before a response reaches the user. You verify that dates "
        "make sense (not accidentally in the past, correct day of the week), that titles are non-empty, "
        "and that write actions returned ok:true in their tool output. "
        "You then rewrite the response in warm, second-person language: 'Your event has been added', "
        "'You have 3 todos due this week', etc. If something looks wrong, flag it clearly. "
        "Your output is the exact text the user will read — concise, correct, and human."
    ),
    llm=_llm,
    tools=[get_calendar_events, get_todos, get_google_calendar_events],
)

# Standalone — not in the main crew; invoked directly for explicit planning requests.
planner_agent = Agent(
    role="Daily Schedule Optimizer",
    goal=(
        "Read the user's current todos and calendar events (both local and Google Calendar), "
        "then produce an optimised time-blocked daily plan that minimises context switching "
        "and respects existing calendar commitments."
    ),
    backstory=(
        "You are an expert in time management and deep work. You know that context switching costs "
        "20+ minutes of productive focus each time, so you batch similar tasks together. Existing "
        "calendar events are hard constraints — you schedule todos around them, never over them. "
        "You always leave 10-minute buffer gaps between blocks. Your output is a readable, hour-by-hour "
        "plan the user can follow immediately, with a brief rationale for the ordering."
    ),
    llm=_llm,
    tools=[get_calendar_events, get_todos, get_google_calendar_events],
)
