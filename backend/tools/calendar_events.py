# Modules for functionality
import argparse
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _ROOT / "backend/storage/calendar_events.json"

parser = argparse.ArgumentParser()
parser.add_argument("--get", action="store_true", help="Gets calendar events")
parser.add_argument("--add", nargs=2, metavar=("TITLE", "DATETIME"), help="Adds a calendar event")
parser.add_argument("--save", metavar="EVENTS", help="Saves calendar events JSON string")
parser.add_argument("--path", default=str(_DEFAULT_PATH), help="Path to the calendar events file")
args = parser.parse_args()

PATH = Path(args.path)

def get_calendar_events():
    try:
        with open(PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_calendar_events(events):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PATH, "w") as f:
        json.dump(events, f, indent=2)

if args.get:
    print(json.dumps(get_calendar_events()))

if args.save:
    save_calendar_events(json.loads(args.save))

if args.add:
    title, datetime_str = args.add
    events = get_calendar_events()
    events.append({"title": title, "datetime": datetime_str})
    save_calendar_events(events)
