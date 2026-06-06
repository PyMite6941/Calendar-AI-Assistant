# Modules for functionality
import subprocess
import sys
from pathlib import Path
# Modules for styling
from rich.console import Console
from rich.panel import Panel
import questionary

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

console = Console()
console.print(Panel.fit("Welcome to the Calendar AI Assistant!", title="Calendar AI Assistant", title_align="center", border_style="blue", padding=(1, 2)))

# Start the background scheduler (10-minute crew ticks)
try:
    from backend.scheduler import start as _start_scheduler, status as _scheduler_status
    _start_scheduler(interval=600)
    _s = _scheduler_status()
    console.print(f"[dim]Scheduler running — crew ticks every {_s['interval_seconds'] // 60} min  ·  log: {_s['log_path']}[/dim]")
except Exception as _e:
    console.print(f"[yellow]Scheduler could not start: {_e}[/yellow]")

choice = questionary.select(
    "How do you want to run the Calendar AI Assistant?",
    choices=[
        "Run in CLI",
        "Run in Streamlit",
        "Install necessary packages",
        "Exit",
    ],
    pointer='>'
).ask()
if choice == "Run in CLI":
    subprocess.run(["python", "frontend/cli/cli.py"], cwd=str(PROJECT_ROOT))
elif choice == "Run in Streamlit":
    subprocess.run(["streamlit", "run", "frontend/streamlit/Page.py"], cwd=str(PROJECT_ROOT))
elif choice == "Install necessary packages":
    platform = sys.platform
    if platform.startswith("win"):
        subprocess.run(["bash", "setup.sh"], cwd=str(PROJECT_ROOT))
    elif platform.startswith("linux") or platform.startswith("darwin"):
        subprocess.run(["chmod", "+x", "setup.sh"], cwd=str(PROJECT_ROOT))
        subprocess.run(["./setup.sh"], cwd=str(PROJECT_ROOT))
    else:
        console.print("[red]Unsupported operating system. Please install the necessary packages manually.[/red]")
else:
    console.print("[cyan]Goodbye![/cyan]")
    sys.exit()