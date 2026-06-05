# Modules for functionality
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.agents.crew import run_calendar_assistant
# Modules for styling
from rich.console import Console

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--start", action="store_true", help="Start the calendar assistant")
parser.add_argument("--request", metavar="TEXT", default=None, help="The user request to process")
args = parser.parse_args()

if args.start:
    user_request = args.request or console.input("[bold cyan]What would you like to do?[/] ").strip()
    if user_request:
        result = run_calendar_assistant(user_request)
        console.print(result)
    else:
        console.print("[yellow]No request provided.[/]")
