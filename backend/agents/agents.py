import subprocess
import sys
import tomllib
import urllib.request
import json
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
        # try prefix match (e.g. "llama3.2" matches "llama3.2:3b")
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


# ── tools ─────────────────────────────────────────────────────────────────────

@tool("get_calendar_events")
def get_calendar_events() -> str:
    """Return all local calendar events as a JSON string."""
    result = subprocess.run(
        [sys.executable, "backend/tools/calendar_events.py", "--get"],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or "[]"


@tool("add_calendar_event")
def add_calendar_event(title: str, start: str, end: str,
                       description: str = "", location: str = "",
                       reminder: int = 0, recurrence: str = "none") -> str:
    """Add a calendar event. start/end: ISO 8601 (YYYY-MM-DDTHH:MM:SS).
    recurrence: none | daily | weekly | monthly."""
    result = subprocess.run(
        [sys.executable, "backend/tools/calendar_events.py", "--add",
         title, start, end, description, location, "", str(reminder), recurrence],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("update_calendar_event")
def update_calendar_event(index: int, patch_json: str) -> str:
    """Update a calendar event by index. patch_json is a JSON object of fields to change."""
    result = subprocess.run(
        [sys.executable, "backend/tools/calendar_events.py", "--update", str(index), "--json", patch_json],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("delete_calendar_event")
def delete_calendar_event(index: int) -> str:
    """Delete a calendar event by its 0-based index."""
    result = subprocess.run(
        [sys.executable, "backend/tools/calendar_events.py", "--delete", str(index)],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("get_todos")
def get_todos() -> str:
    """Return all todo items as a JSON string."""
    result = subprocess.run(
        [sys.executable, "backend/tools/todo_stuff.py", "--get"],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or "[]"


@tool("add_todo")
def add_todo(title: str, description: str = "", priority: str = "medium",
             due_date: str = "", status: str = "pending", notes: str = "") -> str:
    """Add a todo item. priority: low | medium | high. status: pending | in-progress | done."""
    result = subprocess.run(
        [sys.executable, "backend/tools/todo_stuff.py", "--add",
         title, description, priority, due_date, status, "[]", notes],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("update_todo")
def update_todo(index: int, patch_json: str) -> str:
    """Update a todo item by index. patch_json is a JSON object of fields to change."""
    result = subprocess.run(
        [sys.executable, "backend/tools/todo_stuff.py", "--update", str(index), "--json", patch_json],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("delete_todo")
def delete_todo(index: int) -> str:
    """Delete a todo item by its 0-based index."""
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
        "'in four days', 'end of the week'), you resolve it to an absolute date. If a title is missing, "
        "you infer the best one from context. If the intent is ambiguous, you pick the most likely "
        "interpretation and state your assumption. Your output is so structured and complete that "
        "downstream agents never need to re-read the original message."
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
        "You are a precise data librarian for the user's schedule. You know every event and task "
        "stored locally and you retrieve only what's needed. When asked about upcoming events, you pull "
        "them. When asked to update a todo, you find the right one by reading the full list first and "
        "matching by title. You never guess an index — you always read the data before committing to a "
        "position. If nothing relevant exists, you report that clearly so the processor can act accordingly."
    ),
    llm=_llm,
    tools=[get_calendar_events, get_todos, get_config],
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
        "For add actions, you fill in all available fields (title, start, end, location, priority, "
        "due_date, notes) inferred from the user's message. For updates, you build a precise patch JSON "
        "containing only the fields that changed. For questions, you answer in plain, friendly language "
        "using the retrieved data. You never leave a task half-done."
    ),
    llm=_llm,
    tools=[
        get_calendar_events, add_calendar_event, update_calendar_event, delete_calendar_event,
        get_todos, add_todo, update_todo, delete_todo,
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
        "that actions were confirmed by the tool output, and that answers are accurate. "
        "You then rewrite the response in warm, second-person language: 'Your event has been added', "
        "'You have 3 todos due this week', etc. If something looks wrong, you flag it clearly. "
        "Your output is the exact text the user will read — so make it concise, correct, and human."
    ),
    llm=_llm,
    tools=[get_calendar_events, get_todos],
)

# Standalone — not in the main crew; invoked directly for explicit planning requests.
planner_agent = Agent(
    role="Daily Schedule Optimizer",
    goal=(
        "Read the user's current todos and calendar events, then produce an optimised time-blocked "
        "daily plan that minimises context switching and respects existing calendar commitments."
    ),
    backstory=(
        "You are an expert in time management and deep work. You know that context switching costs "
        "20+ minutes of productive focus each time, so you batch similar tasks together. Existing "
        "calendar events are hard constraints — you schedule todos around them, never over them. "
        "You always leave 10-minute buffer gaps between blocks. Your output is a readable, hour-by-hour "
        "plan the user can follow immediately, with a brief rationale for the ordering."
    ),
    llm=_llm,
    tools=[get_calendar_events, get_todos, add_calendar_event, update_calendar_event, update_todo],
)
