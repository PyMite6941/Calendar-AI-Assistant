# Modules for functionality
import argparse
import json
# Modules for styling
from rich.console import Console

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--get", action="store_true", help="Gets calendar events")
parser.add_argument("--add", nargs=2, metavar=("TITLE", "DATETIME"), help="Adds a calendar event")
parser.add_argument("--save", metavar="EVENTS", help="Saves calendar events")
parser.add_argument("--path", default="backend/storage/calendar_events.json", help="Path to the calendar events file")
args = parser.parse_args()

def get_calendar_events():
    try:
        with open(args.path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_calendar_events(events):
    with open(args.path, "w") as file:
        json.dump(events, file)
    return "[bold green]Calendar events saved successfully.[/]"

if args.get:
    console.print(get_calendar_events())

if args.save:
    console.print(save_calendar_events(args.save))
