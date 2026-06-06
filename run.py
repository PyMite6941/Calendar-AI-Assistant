import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
import questionary

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

console = Console()
console.print(Panel.fit(
    "Welcome to the Calendar AI Assistant!",
    title="Calendar AI Assistant",
    title_align="center",
    border_style="blue",
    padding=(1, 2),
))

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
        "Update app",
        "Exit",
    ],
    pointer=">",
).ask()

if choice == "Run in CLI":
    subprocess.run([sys.executable, "frontend/cli/cli.py"], cwd=str(PROJECT_ROOT))

elif choice == "Run in Streamlit":
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "frontend/streamlit/Page.py"],
        cwd=str(PROJECT_ROOT),
    )

elif choice == "Install necessary packages":
    if sys.platform.startswith("win"):
        subprocess.run(["bash", "setup.sh"], cwd=str(PROJECT_ROOT))
    elif sys.platform.startswith(("linux", "darwin")):
        subprocess.run(["chmod", "+x", "setup.sh"], cwd=str(PROJECT_ROOT))
        subprocess.run(["./setup.sh"], cwd=str(PROJECT_ROOT))
    else:
        console.print("[red]Unsupported OS. Install packages manually.[/red]")

elif choice == "Update app":
    console.print("[cyan]Checking for updates…[/cyan]")
    fetch = subprocess.run(
        ["git", "fetch"], cwd=str(PROJECT_ROOT), capture_output=True, text=True
    )
    if fetch.returncode != 0:
        console.print(f"[red]git fetch failed: {fetch.stderr.strip()}[/red]")
    else:
        # Check how many commits behind we are
        behind = subprocess.run(
            ["git", "rev-list", "HEAD..origin/master", "--count"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        )
        count = behind.stdout.strip()
        if count == "0":
            console.print("[green]Already up to date.[/green]")
        else:
            console.print(f"[yellow]{count} new commit(s) available. Pulling…[/yellow]")
            pull = subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True,
            )
            if pull.returncode == 0:
                console.print(f"[green]{pull.stdout.strip()}[/green]")
                console.print("[cyan]Updating dependencies…[/cyan]")
                pip = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
                    cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                )
                if pip.returncode == 0:
                    console.print("[green]Dependencies updated. Restart the app to apply changes.[/green]")
                else:
                    console.print(f"[red]pip install failed: {pip.stderr.strip()}[/red]")
            else:
                console.print(f"[red]git pull failed: {pull.stderr.strip()}[/red]")

else:
    console.print("[cyan]Goodbye![/cyan]")
    sys.exit()
