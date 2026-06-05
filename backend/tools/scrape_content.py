# Modules for functionality
import argparse
from backend.agents.crew import run_calendar_assistant
# Modules for styling
from rich.console import Console

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--start", action="store_true", help="Start the calendar assistant")
args = parser.parse_args()

if args.start:
    run_calendar_assistant()