import subprocess
import sys
from pathlib import Path

from crewai import Agent
from crewai.tools import tool

_ROOT = Path(__file__).resolve().parents[2]


@tool("get_calendar_events")
def get_calendar_events() -> str:
    """Return all local calendar events as a JSON string."""
    result = subprocess.run(
        [sys.executable, "backend/tools/calendar_events.py", "--get"],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or "[]"


@tool("add_calendar_event")
def add_calendar_event(title: str, start: str, end: str) -> str:
    """Add a calendar event. start and end must be ISO 8601 strings (YYYY-MM-DDTHH:MM:SS)."""
    result = subprocess.run(
        [sys.executable, "backend/tools/calendar_events.py", "--add", title, start, end],
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
    """Add a todo item. priority: low|medium|high. status: pending|in-progress|done."""
    result = subprocess.run(
        [sys.executable, "backend/tools/todo_stuff.py", "--add",
         title, description, priority, due_date, status, "[]", notes],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("update_todo")
def update_todo(index: int, patch_json: str) -> str:
    """Update a todo item by index. patch_json is a JSON object with fields to change."""
    result = subprocess.run(
        [sys.executable, "backend/tools/todo_stuff.py", "--update", str(index), "--json", patch_json],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("update_calendar_event")
def update_calendar_event(index: int, patch_json: str) -> str:
    """Update a calendar event by index. patch_json is a JSON object with fields to change."""
    result = subprocess.run(
        [sys.executable, "backend/tools/calendar_events.py", "--update", str(index), "--json", patch_json],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip() or result.stderr.strip()


@tool("get_config")
def get_config(key: str, default: str = "") -> str:
    """Read a config value by key."""
    result = subprocess.run(
        [sys.executable, "backend/tools/config_editing.py", "--key", key, "--default", default],
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip()


intent_analyzer = Agent(
    role="Intent Analyzer",
    goal="Determine exactly what the user is requesting and extract relevant details.",
    backstory=(
        "You are an expert at understanding user requests. "
        "You identify whether a request involves calendar events, "
        "todo items, reminders, schedule questions, or general conversation. "
        "You extract dates, times, titles, and important details."
    ),
)

data_agent = Agent(
    role="Schedule Data Retriever",
    goal="Retrieve relevant calendar events, reminders, and todo information needed to fulfill the user's request.",
    backstory=(
        "You specialize in finding relevant schedule, "
        "calendar, reminder, and todo information. "
        "You gather only the information needed for the current request."
    ),
    tools=[get_calendar_events, get_todos, get_config],
)

processing_agent = Agent(
    role="Schedule Processor",
    goal="Generate the correct response or action based on user intent and retrieved data.",
    backstory=(
        "You convert analyzed requests and retrieved schedule information "
        "into useful actions. You create events, generate todo lists, "
        "suggest reminders, and answer schedule questions."
    ),
    tools=[get_calendar_events, add_calendar_event, update_calendar_event,
           get_todos, add_todo, update_todo],
)

verification_agent = Agent(
    role="Response Verifier",
    goal="Check outputs for accuracy, completeness, and consistency.",
    backstory=(
        "You perform quality control on the work of other agents. "
        "You look for missing information, logical errors, "
        "and incomplete responses before they are returned to the user."
    ),
    tools=[get_calendar_events, get_todos],
)

planner_agent = Agent(
    role="Calendar Planner",
    goal="Turn a list of tasks into an optimized daily schedule",
    backstory=(
        "You are an expert productivity assistant that organizes tasks into efficient "
        "time blocks while minimizing context switching."
    ),
    tools=[get_calendar_events, get_todos, add_calendar_event, update_calendar_event, update_todo],
)
