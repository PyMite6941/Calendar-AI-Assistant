import json
import shutil
import subprocess
import sys
import tomllib
import tomli_w
from pathlib import Path

import questionary
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.auth.add_google_oauth import cli_connect, cli_disconnect, cli_is_connected

PROVIDERS = ["OpenAI", "Groq", "Gemini", "Mistral", "Ollama"]

console = Console()

CALENDAR_PATH = PROJECT_ROOT / "backend/storage/calendar_events.json"
TODOS_PATH    = PROJECT_ROOT / "backend/storage/todos.json"
CONFIGS_PATH  = PROJECT_ROOT / "backend/storage/configs.toml"
SECRETS_PATH  = PROJECT_ROOT / "backend/storage/secrets.toml"


# ── calendar ──────────────────────────────────────────────────────────────────

def get_events():
    try:
        return json.loads(CALENDAR_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_events(events):
    CALENDAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALENDAR_PATH.write_text(json.dumps(events, indent=2))

def calendar_menu():
    while True:
        choice = questionary.select(
            "Calendar", choices=["View events", "Add event", "Delete event", "Back"]
        ).ask()

        if choice == "View events":
            events = get_events()
            if not events:
                console.print("[yellow]No events found.[/]")
            else:
                t = Table(title="Calendar Events", show_lines=True)
                t.add_column("Title"); t.add_column("DateTime")
                for e in events:
                    t.add_row(e.get("title", ""), e.get("datetime", ""))
                console.print(t)

        elif choice == "Add event":
            title = questionary.text("Event title:").ask()
            dt    = questionary.text("DateTime (YYYY-MM-DDTHH:MM:SS):").ask()
            events = get_events()
            events.append({"title": title, "datetime": dt})
            save_events(events)
            console.print("[green]Event added.[/]")

        elif choice == "Delete event":
            events = get_events()
            if not events:
                console.print("[yellow]No events to delete.[/]")
                continue
            labels = [f"{i}: {e.get('title','')} ({e.get('start','')})" for i, e in enumerate(events)]
            pick = questionary.select("Select event to delete:", choices=labels + ["Cancel"]).ask()
            if pick != "Cancel":
                removed = events.pop(int(pick.split(":")[0]))
                save_events(events)
                console.print(f"[green]Deleted: {removed.get('title')}[/]")
        else:
            break


# ── todos ─────────────────────────────────────────────────────────────────────

def get_todos():
    try:
        return json.loads(TODOS_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_todos(todos):
    TODOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TODOS_PATH.write_text(json.dumps(todos, indent=2))

def todo_menu():
    while True:
        choice = questionary.select(
            "Todo List", choices=["View todos", "Add todo", "Delete todo", "Back"]
        ).ask()

        if choice == "View todos":
            todos = get_todos()
            if not todos:
                console.print("[yellow]No todos found.[/]")
            else:
                t = Table(title="Todo List", show_lines=True)
                t.add_column("#"); t.add_column("Title"); t.add_column("Description")
                for i, todo in enumerate(todos):
                    t.add_row(str(i), todo.get("title", ""), todo.get("description", ""))
                console.print(t)

        elif choice == "Add todo":
            title = questionary.text("Title:").ask()
            desc  = questionary.text("Description:").ask()
            todos = get_todos()
            todos.append({"title": title, "description": desc})
            save_todos(todos)
            console.print("[green]Todo added.[/]")

        elif choice == "Delete todo":
            todos = get_todos()
            if not todos:
                console.print("[yellow]No todos to delete.[/]")
                continue
            pick = questionary.select(
                "Select todo to delete:",
                choices=[f"{i}: {t.get('title', '')}" for i, t in enumerate(todos)] + ["Cancel"],
            ).ask()
            if pick != "Cancel":
                todos.pop(int(pick.split(":")[0]))
                save_todos(todos)
                console.print("[green]Deleted.[/]")
        else:
            break


# ── settings ──────────────────────────────────────────────────────────────────

def get_config(key, default=None):
    try:
        with open(CONFIGS_PATH, "rb") as f:
            return tomllib.load(f).get(key, default)
    except FileNotFoundError:
        return default

def set_config(key, value):
    try:
        with open(CONFIGS_PATH, "rb") as f:
            configs = tomllib.load(f)
    except FileNotFoundError:
        configs = {}
    configs[key] = value
    CONFIGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIGS_PATH, "wb") as f:
        tomli_w.dump(configs, f)

def get_secret_top(key, default=None):
    try:
        with open(SECRETS_PATH, "rb") as f:
            return tomllib.load(f).get(key, default)
    except FileNotFoundError:
        return default

def set_secret_top(key, value):
    try:
        with open(SECRETS_PATH, "rb") as f:
            secrets = tomllib.load(f)
    except FileNotFoundError:
        secrets = {}
    secrets[key] = value
    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SECRETS_PATH, "wb") as f:
        tomli_w.dump(secrets, f)

def get_secret(section, key, default=None):
    try:
        with open(SECRETS_PATH, "rb") as f:
            return tomllib.load(f).get(section, {}).get(key, default)
    except FileNotFoundError:
        return default

def set_secret(section, key, value):
    try:
        with open(SECRETS_PATH, "rb") as f:
            secrets = tomllib.load(f)
    except FileNotFoundError:
        secrets = {}
    secrets.setdefault(section, {})[key] = value
    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SECRETS_PATH, "wb") as f:
        tomli_w.dump(secrets, f)

def set_secret_toplevel(key, value):
    try:
        with open(SECRETS_PATH, "rb") as f:
            secrets = tomllib.load(f)
    except FileNotFoundError:
        secrets = {}
    secrets[key] = value
    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SECRETS_PATH, "wb") as f:
        tomli_w.dump(secrets, f)

def settings_menu():
    while True:
        choice = questionary.select(
            "Settings",
            choices=[
                "View settings",
                "Set calendar view",
                "Set notification preferences",
                "Set API provider",
                "Set AI model",
                "Set API key",
                "Google account",
                "Clear cache",
                "Back",
            ],
        ).ask()

        if choice == "View settings":
            provider = get_secret_top("api_provider", "Ollama")
            model = get_secret_top(f"{str(provider).lower()}_model", "not set")
            console.print(Panel(
                f"Calendar view:           {get_config('calendar_view', 'dayGridMonth')}\n"
                f"Notification preferences: {get_config('notification_preferences', 'Email, SMS')}\n"
                f"API provider:            {provider}\n"
                f"AI model:                {model}\n"
                f"API key:                 {'set' if get_secret_top('api_key') else 'not set'}",
                title="Settings",
            ))

        elif choice == "Set calendar view":
            view = questionary.select(
                "Calendar view:", choices=["dayGridMonth", "timeGridWeek", "timeGridDay"]
            ).ask()
            set_config("calendar_view", view)
            console.print("[green]Saved.[/]")

        elif choice == "Set notification preferences":
            prefs = questionary.text(
                "Notification preferences:", default=get_config("notification_preferences", "Email, SMS")
            ).ask()
            if prefs is not None:
                set_config("notification_preferences", prefs)
                console.print("[green]Saved.[/]")

        elif choice == "Set API provider":
            provider = questionary.select("Provider:", choices=PROVIDERS).ask()
            if provider:
                set_secret_top("api_provider", provider)
                console.print("[green]Saved.[/]")

        elif choice == "Set AI model":
            provider = get_secret_top("api_provider", "Ollama")
            model = questionary.text(
                f"AI model for {provider}:",
                default=str(get_secret_top(f"{str(provider).lower()}_model", "")),
            ).ask()
            if model:
                set_secret_top(f"{str(provider).lower()}_model", model)
                console.print("[green]Saved.[/]")

        elif choice == "Set API key":
            key = questionary.password("API key:").ask()
            if key:
                set_secret_top("api_key", key)
                console.print("[green]Saved.[/]")

        elif choice == "Google account":
            google_menu()

        elif choice == "Clear cache":
            removed = 0
            for cache_dir in PROJECT_ROOT.rglob("__pycache__"):
                if cache_dir.exists():
                    shutil.rmtree(cache_dir)
                    removed += 1
            console.print(f"[green]Cache cleared — {removed} folder(s) removed.[/]")
        else:
            break


# ── chat ──────────────────────────────────────────────────────────────────────

def chat_menu():
    console.print(Panel("Type your message. Type [bold]exit[/bold] to go back.", title="AI Chat"))
    history = []
    while True:
        user_input = questionary.text("You:").ask()
        if not user_input or user_input.lower() == "exit":
            break

        history.append(f"You: {user_input}")
        provider = str(get_secret_top("api_provider", "ollama")).lower()
        result = subprocess.run(
            ["python", "backend/tools/connect_to_ai.py", "--ask", user_input, "--provider", provider],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        response = result.stdout.strip() or result.stderr.strip() or "No response."
        history.append(f"AI: {response}")
        console.print(f"[bold cyan]AI:[/] {response}")


# ── google account ────────────────────────────────────────────────────────────

def google_menu():
    connected = cli_is_connected()
    console.print(f"Google account: {'[green]Connected[/]' if connected else '[red]Not connected[/]'}")

    if connected:
        if questionary.confirm("Disconnect Google account?").ask():
            cli_disconnect()
            console.print("[green]Disconnected.[/]")
    else:
        if not get_secret("google", "client_id"):
            console.print("[red]Google OAuth not configured in secrets.toml.[/]")
            return
        if questionary.confirm("Connect Google account?").ask():
            creds = cli_connect()
            console.print("[green]Connected successfully.[/]" if creds else "[red]Connection failed.[/]")


# ── description ─────────────────────────────────────────────────────────────────

def description_menu():
    readme = PROJECT_ROOT / "README.md"
    if readme.exists():
        console.print(Panel(Markdown(readme.read_text()), title="Description", border_style="blue"))
    else:
        console.print("[yellow]No description yet.[/]")


# ── portfolio ───────────────────────────────────────────────────────────────────

def _google_call(*flags):
    result = subprocess.run(
        ["python", "backend/auth/add_google_oauth.py", *flags],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    try:
        return json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {}

def portfolio_menu():
    console.print(Panel.fit(
        "[bold]Calendar AI Assistant — Portfolio[/]\n"
        "A smart, multi-interface calendar and productivity manager powered by AI agents.",
        border_style="magenta",
    ))

    overview = Table(title="At a Glance", show_lines=True)
    overview.add_column("Metric"); overview.add_column("Value")
    overview.add_row("AI Providers", "5 — OpenAI · Groq · Gemini · Mistral · Ollama")
    overview.add_row("Interfaces", "2 — Streamlit web UI + rich CLI")
    overview.add_row("Agent Pipeline", "4 agents — Intent → Retrieve → Process → Verify")
    console.print(overview)

    console.print(Panel(
        "[bold]Calendar Management[/] — add/view/delete events, month/week/day views, Google Calendar sync\n"
        "[bold]AI Chat[/] — natural-language event & task creation, multi-provider, offline via Ollama\n"
        "[bold]Todo List[/] — tasks with descriptions, persistent storage, AI-generated tasks\n"
        "[bold]Google Integration[/] — Calendar read/write, Gmail read-only, secure token storage",
        title="Features",
    ))

    console.print(Panel(
        "Frontend:   Streamlit 1.57 · streamlit-calendar · Rich (CLI)\n"
        "AI/Agents:  CrewAI 1.14 · OpenAI SDK · multi-provider routing\n"
        "Auth/APIs:  google-auth-oauthlib · googleapiclient · TOML config",
        title="Tech Stack",
    ))

    status = _google_call("--status")
    if status.get("connected"):
        console.print(f"Google: [green]Connected[/] as [bold]{status.get('email', 'unknown')}[/] ({status.get('name', '')})")
        if questionary.confirm("Load upcoming Google Calendar events?", default=False).ask():
            events = _google_call("--list-events", "--max", "10")
            if isinstance(events, list) and events:
                t = Table(title="Upcoming Google Events", show_lines=True)
                t.add_column("Title"); t.add_column("Start"); t.add_column("Location")
                for ev in events:
                    t.add_row(ev.get("title", ""), ev.get("start", ""), ev.get("location", ""))
                console.print(t)
            elif isinstance(events, dict) and events.get("error"):
                console.print(f"[red]{events['error']}[/]")
            else:
                console.print("[yellow]No upcoming events.[/]")
    else:
        console.print("Google: [red]Not connected[/] — connect via the Google Account menu to see live data.")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "Welcome to the Calendar AI Assistant",
        title="Calendar AI Assistant",
        border_style="blue",
        padding=(1, 2),
    ))

    while True:
        connected = cli_is_connected()
        google_label = "Google Account [green](connected)[/]" if connected else "Google Account [red](not connected)[/]"

        choice = questionary.select(
            "Main Menu",
            choices=[
                "Description",
                "Portfolio",
                "Calendar",
                "Todo List",
                "Settings",
                "Chat",
                google_label,
                "Exit",
            ],
        ).ask()

        if choice == "Description":         description_menu()
        elif choice == "Portfolio":         portfolio_menu()
        elif choice == "Calendar":          calendar_menu()
        elif choice == "Todo List":         todo_menu()
        elif choice == "Settings":          settings_menu()
        elif choice == "Chat":              chat_menu()
        elif "Google Account" in choice:    google_menu()
        else:
            console.print("[cyan]Goodbye![/cyan]")
            break


if __name__ == "__main__":
    main()
