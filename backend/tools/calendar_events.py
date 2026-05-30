# Modules for functionality
import argparse
# Modules for style
from rich.console import Console

console = Console()
args = argparse.ArgumentParser()
args.add_argument("--get", action="store_true", help="Gets calendar events")
args.add_argument("--save", metavar='EVENTS', help="Saves calendar events")
args.add_argument("--path", default="backend/storage/calendar_events.json", help="Path to the calendar events file")
args = args.parse_args()

def get_calendar_events():
    try:
        with open(args.path, "r") as file:
            return file.read()
    except FileNotFoundError:
        return "[]"
    
def save_calendar_events(events):
    with open(args.path, "w") as file:
        file.write(events)
    return "[bold green]Calendar events saved successfully.[/]" if args.save else "[bold red]Failed to save calendar events.[/]"

if args.get:
    console.print(get_calendar_events())

if args.save:
    console.print(save_calendar_events(args.save))