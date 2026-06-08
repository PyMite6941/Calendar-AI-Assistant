import argparse
import json
import sys
import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import urllib.request
from openai import OpenAI
from rich.console import Console

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
from backend.tools.calendar_events import (
    get_events as _get_events, add_event as _add_event,
    update_event as _update_event, delete_event as _delete_event,
)
from backend.tools.todo_stuff import (
    get_todos as _get_todos_direct, add_todo as _add_todo,
    update_todo as _update_todo, delete_todo as _delete_todo,
)

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--ask",      metavar="QUESTION", required=True, help="Question to ask the AI")
parser.add_argument("--provider", default=None, help="Override provider (groq, gemini, mistral, ollama)")
parser.add_argument("--history",  default="[]", help="JSON array of prior {role, content} messages")
args = parser.parse_args()

_SECRETS_PATH = _ROOT / "backend/storage/secrets.toml"
_CONFIGS_PATH = _ROOT / "backend/storage/configs.toml"

if not _SECRETS_PATH.exists():
    _SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SECRETS_PATH.write_text("[apis]\n")

with open(_SECRETS_PATH, "rb") as f:
    secrets = tomllib.load(f)

try:
    with open(_CONFIGS_PATH, "rb") as f:
        configs = tomllib.load(f)
except FileNotFoundError:
    configs = {}

def _get_ollama_default():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            models = json.loads(r.read()).get("models", [])
            if models:
                return models[0]["name"]
    except Exception:
        pass
    return "llama3.2"

apis = secrets.get("apis", {})

PROVIDERS = {
    "groq":    ("https://api.groq.com/openai/v1", apis.get("groq_api", ""), "llama-3.1-8b-instant"),
    "gemini":  ("https://generativelanguage.googleapis.com/v1beta/openai/", apis.get("gemini_api", ""), "gemini-2.0-flash"),
    "mistral": ("https://api.mistral.ai/v1", apis.get("mistral_api", ""), "mistral-small-latest"),
    "ollama":  ("http://localhost:11434/v1", "ollama", _get_ollama_default()),
}

provider = (args.provider or secrets.get("api_provider") or apis.get("api_provider", "ollama")).lower()

if provider not in PROVIDERS:
    console.print(f"[bold red]Unknown provider '{provider}'. Choose from: {', '.join(PROVIDERS)}[/]")
    exit(1)

base_url, api_key, model = PROVIDERS[provider]
# use model from settings if saved, fall back to provider default
model = secrets.get(f"{provider}_model") or model
# use generic api_key from settings if provider-specific key is missing
api_key = api_key or secrets.get("api_key", "")

if not api_key and provider != "ollama":
    console.print(f"[bold red]No API key set for '{provider}' in secrets.toml.[/]")
    exit(1)

# ── build runtime context ─────────────────────────────────────────────────────

def _build_context() -> str:
    tz_name = configs.get("timezone", "")
    try:
        tz = ZoneInfo(tz_name) if tz_name else None
    except ZoneInfoNotFoundError:
        tz = None
    now = datetime.now(tz) if tz else datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    lines = [
        f"Today is {now.strftime('%A, %B %d, %Y')} and the current time is {now.strftime('%H:%M')}.",
    ]
    if tz_name:
        lines.append(f"The user's timezone is {tz_name}.")

    user_name = configs.get("user_name", "").strip()
    if user_name:
        lines.append(f"The user's name is {user_name}.")

    notif = configs.get("notification_preferences", "").strip()
    if notif:
        lines.append(f"The user's notification preferences are: {notif}.")

    wh_start = configs.get("working_hours_start", "").strip()
    wh_end   = configs.get("working_hours_end", "").strip()
    if wh_start and wh_end:
        lines.append(f"The user's working hours are {wh_start} to {wh_end}.")

    cal_view = configs.get("calendar_view", "").strip()
    if cal_view:
        lines.append(f"The user prefers the {cal_view} calendar view.")

    events = _get_events()
    if events:
        indexed  = [{**e, "index": i} for i, e in enumerate(events)]
        upcoming = [e for e in indexed if e.get("start", "") >= today_str]
        display  = upcoming[:10] if upcoming else indexed[:5]
        lines.append(
            f"\nCurrent calendar events ({len(events)} total, showing up to 10 upcoming):\n"
            + json.dumps(display, indent=2)
        )
    else:
        lines.append("\nThe user has no calendar events yet.")

    todos = _get_todos_direct()
    if todos:
        indexed = [{**t, "index": i} for i, t in enumerate(todos)]
        active  = [t for t in indexed if t.get("status", "") != "done"][:10]
        lines.append(
            f"\nCurrent todos ({len(todos)} total, showing up to 10 non-done):\n"
            + json.dumps(active, indent=2)
        )
    else:
        lines.append("\nThe user has no todos yet.")

    return "\n".join(lines)


SYSTEM_PROMPT = f"""You are a Calendar and Todo AI Assistant.

--- Context ---
{_build_context()}
---------------

When the user wants to add a todo item, respond with exactly:
{{"action": "add_todo", "title": "...", "description": "...", "priority": "low|medium|high", "due_date": "YYYY-MM-DD or empty", "status": "pending|in-progress|done", "tags": ["tag1"], "notes": "..."}}

When the user wants to update an existing todo, respond with exactly (include only the fields to change):
{{"action": "update_todo", "index": <index from context>, "title": "...", "status": "...", ...}}

When the user wants to delete a todo, respond with exactly:
{{"action": "delete_todo", "index": <index from context>}}

When the user wants to add a calendar event, respond with exactly:
{{"action": "add_event", "title": "...", "start": "YYYY-MM-DDTHH:MM:SS", "end": "YYYY-MM-DDTHH:MM:SS", "description": "...", "location": "...", "color": "", "reminder": 15, "recurrence": "none|daily|weekly|monthly"}}

When the user wants to update an existing calendar event, respond with exactly (include only the fields to change):
{{"action": "update_event", "index": <index from context>, "title": "...", "start": "...", ...}}

When the user wants to delete a calendar event, respond with exactly:
{{"action": "delete_event", "index": <index from context>}}

For all other messages, respond with exactly:
{{"action": "chat", "message": "..."}}

Always respond with valid JSON only. No extra text. Use the date above to resolve relative dates like "tomorrow" or "next Monday". Infer reasonable values for optional fields. Use the "index" field shown in the context to identify existing items."""

try:
    prior_messages = []
    try:
        prior_messages = json.loads(args.history or "[]")
        if not isinstance(prior_messages, list):
            prior_messages = []
    except json.JSONDecodeError:
        prior_messages = []

    client = OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *prior_messages,
            {"role": "user", "content": args.ask},
        ],
    )
    raw = response.choices[0].message.content.strip()
    _TODO_FIELDS  = {"title", "description", "priority", "due_date", "status", "tags", "notes"}
    _EVENT_FIELDS = {"title", "start", "end", "description", "location", "color", "reminder", "recurrence"}

    def _safe_index(d: dict) -> int:
        try:
            return int(d.get("index", -1))
        except (TypeError, ValueError):
            return -1

    try:
        data = json.loads(raw)
        action = data.get("action", "chat")
        if action == "add_todo":
            title    = str(data.get("title") or "")
            desc     = str(data.get("description") or "")
            priority = str(data.get("priority") or "medium")
            due_date = str(data.get("due_date") or "")
            status   = str(data.get("status") or "pending")
            raw_tags = data.get("tags")
            if isinstance(raw_tags, list):
                tags = raw_tags
            elif isinstance(raw_tags, str) and raw_tags.strip():
                tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
            else:
                tags = []
            notes    = str(data.get("notes") or "")
            _add_todo(title, desc, priority, due_date, status, tags, notes)
            print(f"Done — added todo: {title}")
        elif action == "update_todo":
            index = _safe_index(data)
            patch = {k: v for k, v in data.items() if k in _TODO_FIELDS}
            if index >= 0 and patch:
                result = _update_todo(index, patch)
                if result.get("ok"):
                    print(f"Done — updated todo: {result.get('todo', {}).get('title', '')}")
                else:
                    print(f"Error updating todo: {result.get('error', 'unknown error')}")
            else:
                print("Could not update todo — missing index or no valid fields to change.")
        elif action == "delete_todo":
            index = _safe_index(data)
            if index >= 0:
                result = _delete_todo(index)
                if result.get("ok"):
                    print(f"Done — deleted todo: {result.get('todo', {}).get('title', '')}")
                else:
                    print(f"Error deleting todo: {result.get('error', 'unknown error')}")
            else:
                print("Could not delete todo — missing index.")
        elif action == "add_event":
            title       = str(data.get("title") or "")
            start       = str(data.get("start") or "")
            end         = str(data.get("end") or start)
            description = str(data.get("description") or "")
            location    = str(data.get("location") or "")
            color       = str(data.get("color") or "")
            try:
                reminder = int(data.get("reminder") or 0)
            except (TypeError, ValueError):
                reminder = 0
            recurrence  = str(data.get("recurrence") or "none")
            _add_event(title, start, end, description, location, color, reminder, recurrence)
            print(f"Done — added event: {title}")
        elif action == "update_event":
            index = _safe_index(data)
            patch = {k: v for k, v in data.items() if k in _EVENT_FIELDS}
            if index >= 0 and patch:
                result = _update_event(index, patch)
                if result.get("ok"):
                    print(f"Done — updated event: {result.get('event', {}).get('title', '')}")
                else:
                    print(f"Error updating event: {result.get('error', 'unknown error')}")
            else:
                print("Could not update event — missing index or no valid fields to change.")
        elif action == "delete_event":
            index = _safe_index(data)
            if index >= 0:
                result = _delete_event(index)
                if result.get("ok"):
                    print(f"Done — deleted event: {result.get('event', {}).get('title', '')}")
                else:
                    print(f"Error deleting event: {result.get('error', 'unknown error')}")
            else:
                print("Could not delete event — missing index.")
        else:
            print(data.get("message", raw))
    except json.JSONDecodeError:
        print(raw)
except Exception as e:
    console.print(f"[bold red]Error: {e}[/]")
    exit(1)
