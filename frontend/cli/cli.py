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

_EVENT_DEFAULTS = {
    "title": "", "start": "", "end": "",
    "description": "", "location": "", "color": "",
    "reminder": 0, "recurrence": "none",
}
_TODO_DEFAULTS = {
    "title": "", "description": "", "priority": "medium",
    "due_date": "", "status": "pending", "tags": [], "notes": "",
}

def _ce(e: dict) -> dict:
    return {**_EVENT_DEFAULTS, **e}

def _ct(t: dict) -> dict:
    return {**_TODO_DEFAULTS, **t}


# ── calendar ──────────────────────────────────────────────────────────────────

def get_events():
    try:
        return [_ce(e) for e in json.loads(CALENDAR_PATH.read_text())]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_events(events):
    CALENDAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALENDAR_PATH.write_text(json.dumps(events, indent=2))

def _safe_select(prompt, choices, current):
    default = current if current in choices else choices[0]
    return questionary.select(prompt, choices=choices, default=default).ask()

def calendar_menu():
    while True:
        choice = questionary.select(
            "Calendar",
            choices=["View events", "Add event", "Edit event", "Delete event", "Back"],
        ).ask()

        if choice == "View events":
            events = get_events()
            if not events:
                console.print("[yellow]No events.[/]")
            else:
                t = Table(title="Calendar Events", show_lines=True)
                t.add_column("#",           style="dim", width=3)
                t.add_column("Title",       style="bold")
                t.add_column("Start")
                t.add_column("End")
                t.add_column("Location",    style="dim")
                t.add_column("Recurrence",  style="dim")
                t.add_column("Reminder",    style="dim")
                for i, e in enumerate(events):
                    reminder_str = f"{e['reminder']} min" if e.get("reminder") else "—"
                    t.add_row(
                        str(i),
                        e.get("title", ""),
                        e.get("start", ""),
                        e.get("end", ""),
                        e.get("location", "") or "—",
                        e.get("recurrence", "none"),
                        reminder_str,
                    )
                console.print(t)
                # Detail view option
                labels = [f"{i}: {e.get('title','')} ({e.get('start','')})" for i, e in enumerate(events)]
                pick = questionary.select("View details or Back:", choices=labels + ["Back"]).ask()
                if pick != "Back":
                    idx = int(pick.split(":")[0])
                    ev = events[idx]
                    console.print(Panel(
                        f"[bold]Title:[/]       {ev.get('title','')}\n"
                        f"[bold]Start:[/]       {ev.get('start','')}\n"
                        f"[bold]End:[/]         {ev.get('end','')}\n"
                        f"[bold]Description:[/] {ev.get('description','') or '—'}\n"
                        f"[bold]Location:[/]    {ev.get('location','') or '—'}\n"
                        f"[bold]Recurrence:[/]  {ev.get('recurrence','none')}\n"
                        f"[bold]Reminder:[/]    {ev.get('reminder',0)} min before",
                        title=ev.get("title", "Event"),
                        border_style="cyan",
                    ))

        elif choice == "Add event":
            title       = questionary.text("Title:").ask() or ""
            start       = questionary.text("Start (YYYY-MM-DDTHH:MM:SS):").ask() or ""
            end         = questionary.text("End (blank = same as start):").ask() or start
            description = questionary.text("Description (optional):").ask() or ""
            location    = questionary.text("Location (optional):").ask() or ""
            recurrence  = questionary.select("Recurrence:", choices=["none","daily","weekly","monthly"]).ask()
            reminder    = questionary.text("Reminder minutes before (0 = off):").ask() or "0"
            events = get_events()
            events.append({
                **_EVENT_DEFAULTS,
                "title": title, "start": start, "end": end,
                "description": description, "location": location,
                "reminder": int(reminder), "recurrence": recurrence,
            })
            save_events(events)
            console.print("[green]Event added.[/]")

        elif choice == "Edit event":
            events = get_events()
            if not events:
                console.print("[yellow]No events to edit.[/]")
                continue
            labels = [f"{i}: {e.get('title','')} ({e.get('start','')})" for i, e in enumerate(events)]
            pick = questionary.select("Select event:", choices=labels + ["Cancel"]).ask()
            if pick == "Cancel":
                continue
            idx = int(pick.split(":")[0])
            ev  = events[idx]
            patch = {
                "title":       questionary.text("Title:",       default=ev["title"]).ask() or ev["title"],
                "start":       questionary.text("Start:",       default=ev["start"]).ask() or ev["start"],
                "end":         questionary.text("End:",         default=ev["end"]).ask()   or ev["end"],
                "description": questionary.text("Description:", default=ev["description"]).ask() or "",
                "location":    questionary.text("Location:",    default=ev["location"]).ask() or "",
                "reminder":    int(questionary.text("Reminder (min):", default=str(ev["reminder"])).ask() or "0"),
                "recurrence":  _safe_select("Recurrence:", ["none","daily","weekly","monthly"], ev["recurrence"]),
            }
            events[idx] = {**ev, **patch}
            save_events(events)
            console.print("[green]Event updated.[/]")

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
        return [_ct(t) for t in json.loads(TODOS_PATH.read_text())]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_todos(todos):
    TODOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TODOS_PATH.write_text(json.dumps(todos, indent=2))

_PRIORITY_ICON = {"high": "[red]●[/]", "medium": "[yellow]●[/]", "low": "[green]●[/]"}
_STATUS_ICON   = {"pending": "⬜", "in-progress": "🔵", "done": "✅"}

def todo_menu():
    while True:
        choice = questionary.select(
            "Todo List",
            choices=["View todos", "Add todo", "Edit todo", "Delete todo", "Back"],
        ).ask()

        if choice == "View todos":
            todos = get_todos()
            if not todos:
                console.print("[yellow]No todos.[/]")
            else:
                t = Table(title="Todo List", show_lines=True)
                t.add_column("#",        style="dim", width=3)
                t.add_column("Status",   width=4)
                t.add_column("P",        width=3)
                t.add_column("Title",    style="bold")
                t.add_column("Due",      style="dim")
                t.add_column("Description")
                for i, todo in enumerate(todos):
                    p  = todo.get("priority", "medium")
                    st = todo.get("status",   "pending")
                    t.add_row(
                        str(i),
                        _STATUS_ICON.get(st, ""),
                        _PRIORITY_ICON.get(p, ""),
                        todo.get("title", ""),
                        todo.get("due_date", "") or "—",
                        todo.get("description", ""),
                    )
                console.print(t)
                # Detail view option
                labels = [f"{i}: {td.get('title','')} [{td.get('status','pending')}]" for i, td in enumerate(todos)]
                pick = questionary.select("View details or Back:", choices=labels + ["Back"]).ask()
                if pick != "Back":
                    idx  = int(pick.split(":")[0])
                    todo = todos[idx]
                    tags_str = ", ".join(todo.get("tags", [])) or "—"
                    console.print(Panel(
                        f"[bold]Title:[/]       {todo.get('title','')}\n"
                        f"[bold]Status:[/]      {todo.get('status','pending')}\n"
                        f"[bold]Priority:[/]    {todo.get('priority','medium')}\n"
                        f"[bold]Due:[/]         {todo.get('due_date','') or '—'}\n"
                        f"[bold]Description:[/] {todo.get('description','') or '—'}\n"
                        f"[bold]Tags:[/]        {tags_str}\n"
                        f"[bold]Notes:[/]       {todo.get('notes','') or '—'}",
                        title=todo.get("title", "Todo"),
                        border_style="blue",
                    ))

        elif choice == "Add todo":
            title    = questionary.text("Title:").ask() or ""
            desc     = questionary.text("Description:").ask() or ""
            priority = questionary.select("Priority:", choices=["low","medium","high"]).ask()
            due_date = questionary.text("Due date (YYYY-MM-DD, or blank):").ask() or ""
            notes    = questionary.text("Notes (optional):").ask() or ""
            todos = get_todos()
            todos.append({
                **_TODO_DEFAULTS,
                "title": title, "description": desc,
                "priority": priority, "due_date": due_date, "notes": notes,
            })
            save_todos(todos)
            console.print("[green]Todo added.[/]")

        elif choice == "Edit todo":
            todos = get_todos()
            if not todos:
                console.print("[yellow]No todos to edit.[/]")
                continue
            pick = questionary.select(
                "Select todo:",
                choices=[f"{i}: {t.get('title','')} [{t.get('status','pending')}]"
                         for i, t in enumerate(todos)] + ["Cancel"],
            ).ask()
            if pick == "Cancel":
                continue
            idx  = int(pick.split(":")[0])
            todo = todos[idx]
            patch = {
                "title":       questionary.text("Title:",       default=todo["title"]).ask()       or todo["title"],
                "description": questionary.text("Description:", default=todo["description"]).ask() or "",
                "priority":    _safe_select("Priority:", ["low","medium","high"], todo["priority"]),
                "status":      _safe_select("Status:", ["pending","in-progress","done"], todo["status"]),
                "due_date":    questionary.text("Due date:", default=todo["due_date"]).ask() or "",
                "notes":       questionary.text("Notes:",    default=todo["notes"]).ask() or "",
            }
            todos[idx] = {**todo, **patch}
            save_todos(todos)
            console.print("[green]Todo updated.[/]")

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

def settings_menu():
    while True:
        choice = questionary.select(
            "Settings",
            choices=[
                "View settings",
                "Set name",
                "Set timezone",
                "Set working hours",
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
            model    = get_secret_top(f"{str(provider).lower()}_model", "not set")
            wh_s = get_config("working_hours_start", "09:00")
            wh_e = get_config("working_hours_end",   "18:00")
            console.print(Panel(
                f"[bold]Name:[/]                     {get_config('user_name', 'not set')}\n"
                f"[bold]Timezone:[/]                 {get_config('timezone', 'not set (uses system time)')}\n"
                f"[bold]Working hours:[/]            {wh_s} – {wh_e}\n"
                f"[bold]Calendar view:[/]            {get_config('calendar_view', 'dayGridMonth')}\n"
                f"[bold]Notification preferences:[/]  {get_config('notification_preferences', 'Email, SMS')}\n"
                f"[bold]API provider:[/]             {provider}\n"
                f"[bold]AI model:[/]                 {model}\n"
                f"[bold]API key:[/]                  {'set' if get_secret_top('api_key') else 'not set'}",
                title="Settings",
            ))

        elif choice == "Set name":
            name = questionary.text(
                "Your name:", default=get_config("user_name", "")
            ).ask()
            if name is not None:
                set_config("user_name", name.strip())
                console.print("[green]Saved.[/]")

        elif choice == "Set timezone":
            tz = questionary.text(
                "Timezone (IANA format, e.g. Asia/Bangkok, America/New_York):",
                default=get_config("timezone", ""),
            ).ask()
            if tz is not None:
                set_config("timezone", tz.strip())
                console.print("[green]Saved.[/]")

        elif choice == "Set working hours":
            wh_s = questionary.text(
                "Working hours start (HH:MM):",
                default=str(get_config("working_hours_start", "09:00")),
            ).ask()
            wh_e = questionary.text(
                "Working hours end (HH:MM):",
                default=str(get_config("working_hours_end", "18:00")),
            ).ask()
            if wh_s is not None:
                set_config("working_hours_start", wh_s.strip())
            if wh_e is not None:
                set_config("working_hours_end", wh_e.strip())
            console.print("[green]Saved.[/]")

        elif choice == "Set calendar view":
            view = questionary.select(
                "Calendar view:", choices=["dayGridMonth", "timeGridWeek", "timeGridDay"]
            ).ask()
            set_config("calendar_view", view)
            console.print("[green]Saved.[/]")

        elif choice == "Set notification preferences":
            prefs = questionary.text(
                "Notification preferences:",
                default=get_config("notification_preferences", "Email, SMS"),
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


# ── daily planner ─────────────────────────────────────────────────────────────

_PLAN_TRIGGERS = {
    "plan my day", "plan my schedule", "daily plan", "optimize my schedule",
    "optimise my schedule", "schedule my day", "time block my day", "plan today",
    "organize my day", "organise my day",
}

def _is_planning_request(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _PLAN_TRIGGERS)


def planner_menu():
    plan_path = PROJECT_ROOT / "backend/storage/daily_plan.json"

    while True:
        plan_data = {}
        if plan_path.exists():
            try:
                plan_data = json.loads(plan_path.read_text())
            except json.JSONDecodeError:
                pass

        if plan_data:
            gen_at    = plan_data.get("generated_at", "")[:19].replace("T", " ")
            plan_date = plan_data.get("plan_date", "")
            console.print(Panel(
                plan_data.get("plan_text", ""),
                title=f"Daily Plan — {plan_date}  (generated {gen_at})",
                border_style="green",
            ))
        else:
            console.print("[yellow]No plan saved yet.[/]")

        choice = questionary.select(
            "Daily Planner",
            choices=["Generate new plan", "Back"],
        ).ask()

        if choice == "Generate new plan":
            console.print("[cyan]Building your plan...[/]")
            result = subprocess.run(
                [sys.executable, "backend/agents/planner_crew.py"],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            )
            if result.returncode == 0:
                console.print("[green]Plan generated.[/]")
            else:
                console.print(f"[red]Error: {(result.stderr or result.stdout)[:300]}[/]")
        else:
            break


# ── chat ──────────────────────────────────────────────────────────────────────

def chat_menu():
    console.print(Panel(
        "Tell me to add events or todos, ask about your schedule, or just chat.\n"
        "Type [bold]exit[/bold] to go back.",
        title="AI Chat",
    ))
    history = []
    while True:
        user_input = questionary.text("You:").ask()
        if not user_input or user_input.lower() == "exit":
            break

        history.append(f"You: {user_input}")
        if _is_planning_request(user_input):
            console.print("[cyan]Building your plan...[/]")
            result = subprocess.run(
                [sys.executable, "backend/agents/planner_crew.py"],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            )
            if result.returncode == 0:
                response = result.stdout.strip() or "Plan generated — open Daily Planner to view it."
            else:
                response = f"Failed to generate plan: {(result.stderr or result.stdout)[:300]}"
        else:
            provider = str(get_secret_top("api_provider", "ollama")).lower()
            result = subprocess.run(
                [sys.executable, "backend/tools/connect_to_ai.py",
                 "--ask", user_input, "--provider", provider],
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


# ── description ───────────────────────────────────────────────────────────────

def description_menu():
    readme = PROJECT_ROOT / "README.md"
    if readme.exists():
        console.print(Panel(Markdown(readme.read_text()), title="Description", border_style="blue"))
    else:
        console.print("[yellow]No description yet.[/]")


# ── portfolio ─────────────────────────────────────────────────────────────────

def _google_call(*flags):
    result = subprocess.run(
        [sys.executable, "backend/auth/add_google_oauth.py", *flags],
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
    overview.add_row("AI Providers",   "5 — OpenAI · Groq · Gemini · Mistral · Ollama")
    overview.add_row("Interfaces",     "2 — Streamlit web UI + Rich CLI")
    overview.add_row("Agent Pipeline", "4 agents — Intent → Retrieve → Process → Verify")
    console.print(overview)

    console.print(Panel(
        "[bold]Calendar Management[/] — add/view/edit/delete events, location, reminders, recurrence\n"
        "[bold]AI Chat[/]            — natural-language event & task creation, multi-provider, offline via Ollama\n"
        "[bold]Todo List[/]          — priority, status, due date, tags, notes; add/edit/delete\n"
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
        console.print(f"Google: [green]Connected[/] as [bold]{status.get('email','unknown')}[/] ({status.get('name','')})")
        if questionary.confirm("Load upcoming Google Calendar events?", default=False).ask():
            events = _google_call("--list-events", "--max", "10")
            if isinstance(events, list) and events:
                t = Table(title="Upcoming Google Events", show_lines=True)
                t.add_column("Title"); t.add_column("Start"); t.add_column("Location")
                for ev in events:
                    t.add_row(ev.get("title",""), ev.get("start",""), ev.get("location","") or "—")
                console.print(t)
            elif isinstance(events, dict) and events.get("error"):
                console.print(f"[red]{events['error']}[/]")
            else:
                console.print("[yellow]No upcoming events.[/]")
    else:
        console.print("Google: [red]Not connected[/] — use the Google Account menu to connect.")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "Welcome to the Calendar AI Assistant",
        title="Calendar AI Assistant",
        border_style="blue",
        padding=(1, 2),
    ))

    while True:
        connected    = cli_is_connected()
        google_label = (
            "Google Account [green](connected)[/]"
            if connected else
            "Google Account [red](not connected)[/]"
        )

        choice = questionary.select(
            "Main Menu",
            choices=["Description", "Portfolio", "Calendar", "Todo List",
                     "Daily Planner", "Settings", "Chat", google_label, "Exit"],
        ).ask()

        if   choice == "Description":        description_menu()
        elif choice == "Portfolio":          portfolio_menu()
        elif choice == "Calendar":           calendar_menu()
        elif choice == "Todo List":          todo_menu()
        elif choice == "Daily Planner":      planner_menu()
        elif choice == "Settings":           settings_menu()
        elif choice == "Chat":               chat_menu()
        elif "Google Account" in choice:     google_menu()
        else:
            console.print("[cyan]Goodbye![/cyan]")
            break


if __name__ == "__main__":
    main()
