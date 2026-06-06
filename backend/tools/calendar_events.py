import argparse
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _ROOT / "backend/storage/calendar_events.json"

parser = argparse.ArgumentParser()
parser.add_argument("--get",    action="store_true", help="Get all events")
parser.add_argument("--add",    nargs="+", metavar="ARG", help="Add: TITLE START [END] [description] [location] [color] [reminder] [recurrence]")
parser.add_argument("--save",   metavar="EVENTS", help="Overwrite with JSON array")
parser.add_argument("--delete", metavar="ID", type=int, help="Delete event by index")
parser.add_argument("--update", metavar="ID", type=int, help="Update event by index (requires --json)")
parser.add_argument("--json",   metavar="PAYLOAD", help="JSON object of fields to merge (used with --update)")
parser.add_argument("--path",   default=str(_DEFAULT_PATH), help="Path to the events file")
args = parser.parse_args()

PATH = Path(args.path)

_DEFAULTS = {
    "title":       "",
    "start":       "",
    "end":         "",
    "description": "",
    "location":    "",
    "color":       "",
    "reminder":    0,
    "recurrence":  "none",
}

def _coerce(ev: dict) -> dict:
    return {**_DEFAULTS, **ev}

def get_events():
    try:
        with open(PATH, "r") as f:
            return [_coerce(e) for e in json.load(f)]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_events(events):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PATH, "w") as f:
        json.dump(events, f, indent=2)

if args.get:
    print(json.dumps(get_events()))

elif args.save:
    save_events(json.loads(args.save))

elif args.add:
    a = args.add
    event = {
        "title":       a[0] if len(a) > 0 else "",
        "start":       a[1] if len(a) > 1 else "",
        "end":         a[2] if len(a) > 2 else (a[1] if len(a) > 1 else ""),
        "description": a[3] if len(a) > 3 else "",
        "location":    a[4] if len(a) > 4 else "",
        "color":       a[5] if len(a) > 5 else "",
        "reminder":    int(a[6]) if len(a) > 6 else 0,
        "recurrence":  a[7] if len(a) > 7 else "none",
    }
    events = get_events()
    events.append(event)
    save_events(events)

elif args.delete is not None:
    events = get_events()
    if 0 <= args.delete < len(events):
        events.pop(args.delete)
        save_events(events)

elif args.update is not None:
    events = get_events()
    if 0 <= args.update < len(events) and args.json:
        patch = json.loads(args.json)
        events[args.update] = {**events[args.update], **patch}
        save_events(events)
