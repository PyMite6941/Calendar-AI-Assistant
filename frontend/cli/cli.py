import json
import sys
import tomllib
import tomli_w
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.auth.add_google_oauth import cli_connect, cli_disconnect, is_connected

console = Console()

CALENDAR_PATH = PROJECT_ROOT / "backend/storage/calendar_events.json"
TODOS_PATH    = PROJECT_ROOT / "backend/storage/todos.txt"
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
                t.add_column("Title"); t.add_column("Start"); t.add_column("End")
                for e in events:
                    t.add_row(e.get("title", ""), e.get("start", ""), e.get("end", ""))
                console.print(t)

        elif choice == "Add event":
            title = questionary.text("Event title:").ask()
            start = questionary.text("Start (YYYY-MM-DD or datetime):").ask()
            end   = questionary.text("End (YYYY-MM-DD or datetime):").ask()
            events = get_events()
            events.append({"title": title, "start": start, "end": end})
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
        return [l.strip() for l in TODOS_PATH.read_text().splitlines() if l.strip()]
    except FileNotFoundError:
        return []

def save_todos(todos):
    TODOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TODOS_PATH.write_text("\n".join(todos) + ("\n" if todos else ""))

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
                for i, t in enumerate(todos):
                    console.print(f"[cyan]{i}[/] {t}")

        elif choice == "Add todo":
            title = questionary.text("Title:").ask()
            desc  = questionary.text("Description:").ask()
            todos = get_todos()
            todos.append(f"{title}: {desc}")
            save_todos(todos)
            console.print("[green]Todo added.[/]")

        elif choice == "Delete todo":
            todos = get_todos()
            if not todos:
                console.print("[yellow]No todos to delete.[/]")
                continue
            pick = questionary.select(
                "Select todo to delete:",
                choices=[f"{i}: {t}" for i, t in enumerate(todos)] + ["Cancel"],
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

def settings_menu():
    while True:
        choice = questionary.select(
            "Settings",
            choices=["View settings", "Set calendar view", "Set API provider", "Set API key", "Back"],
        ).ask()

        if choice == "View settings":
            console.print(Panel(
                f"Calendar view: {get_config('calendar_view', 'dayGridMonth')}\n"
                f"API provider:  {get_secret('apis', 'api', '')}\n"
                f"API key:       {'set' if get_secret('apis', 'api_key') else 'not set'}",
                title="Settings",
            ))

        elif choice == "Set calendar view":
            view = questionary.select(
                "Calendar view:", choices=["dayGridMonth", "timeGridWeek", "timeGridDay"]
            ).ask()
            set_config("calendar_view", view)
            console.print("[green]Saved.[/]")

        elif choice == "Set API provider":
            set_secret("apis", "api", questionary.text("API provider:").ask())
            console.print("[green]Saved.[/]")

        elif choice == "Set API key":
            set_secret("apis", "api_key", questionary.password("API key:").ask())
            console.print("[green]Saved.[/]")
        else:
            break


# ── chat ──────────────────────────────────────────────────────────────────────

def chat_menu():
    console.print(Panel("Type your message. Type [bold]exit[/bold] to go back.", title="AI Chat"))
    while True:
        user_input = questionary.text("You:").ask()
        if not user_input or user_input.lower() == "exit":
            break
        console.print(f"[dim]Assistant: (agents not yet configured)[/]")


# ── google account ────────────────────────────────────────────────────────────

def google_menu():
    connected = is_connected()
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


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "Welcome to the Calendar AI Assistant",
        title="Calendar AI Assistant",
        border_style="blue",
        padding=(1, 2),
    ))

    while True:
        connected = is_connected()
        google_label = "Google Account [green](connected)[/]" if connected else "Google Account [red](not connected)[/]"

        choice = questionary.select(
            "Main Menu",
            choices=["Calendar", "Todo List", "Settings", "Chat", google_label, "Exit"],
        ).ask()

        if choice == "Calendar":            calendar_menu()
        elif choice == "Todo List":         todo_menu()
        elif choice == "Settings":          settings_menu()
        elif choice == "Chat":              chat_menu()
        elif "Google Account" in choice:    google_menu()
        else:
            console.print("[cyan]Goodbye![/cyan]")
            break


if __name__ == "__main__":
    main()
