import argparse
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _ROOT / "backend/storage/calendar_events.json"

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


def get_events(path: Path = _DEFAULT_PATH) -> list:
    try:
        with open(path, "r") as f:
            return [_coerce(e) for e in json.load(f)]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_events(events: list, path: Path = _DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(events, f, indent=2)


def add_event(title: str, start: str, end: str = "", description: str = "",
              location: str = "", color: str = "", reminder: int = 0,
              recurrence: str = "none", path: Path = _DEFAULT_PATH) -> dict:
    event = _coerce({
        "title": title, "start": start, "end": end or start,
        "description": description, "location": location,
        "color": color, "reminder": int(reminder), "recurrence": recurrence,
    })
    events = get_events(path)
    events.append(event)
    save_events(events, path)
    return {"ok": True, "action": "added", "event": event}


def delete_event(index: int, path: Path = _DEFAULT_PATH) -> dict:
    events = get_events(path)
    if not events:
        return {"ok": False, "error": "No events to delete"}
    if 0 <= index < len(events):
        removed = events.pop(index)
        save_events(events, path)
        return {"ok": True, "action": "deleted", "event": removed}
    return {"ok": False, "error": f"Index {index} out of range (0–{len(events) - 1})"}


def update_event(index: int, patch: dict, path: Path = _DEFAULT_PATH) -> dict:
    events = get_events(path)
    if not events:
        return {"ok": False, "error": "No events to update"}
    if not (0 <= index < len(events)):
        return {"ok": False, "error": f"Index {index} out of range (0–{len(events) - 1})"}
    events[index] = {**events[index], **patch}
    save_events(events, path)
    return {"ok": True, "action": "updated", "event": events[index]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--get",    action="store_true")
    parser.add_argument("--add",    nargs="+", metavar="ARG")
    parser.add_argument("--save",   metavar="EVENTS")
    parser.add_argument("--delete", metavar="ID", type=int)
    parser.add_argument("--update", metavar="ID", type=int)
    parser.add_argument("--json",   metavar="PAYLOAD")
    parser.add_argument("--path",   default=str(_DEFAULT_PATH))
    args = parser.parse_args()
    PATH = Path(args.path)

    if args.get:
        print(json.dumps(get_events(PATH)))
    elif args.save:
        save_events(json.loads(args.save), PATH)
    elif args.add:
        a = args.add
        print(json.dumps(add_event(
            title=a[0] if len(a) > 0 else "",
            start=a[1] if len(a) > 1 else "",
            end=a[2] if len(a) > 2 else (a[1] if len(a) > 1 else ""),
            description=a[3] if len(a) > 3 else "",
            location=a[4] if len(a) > 4 else "",
            color=a[5] if len(a) > 5 else "",
            reminder=int(a[6]) if len(a) > 6 else 0,
            recurrence=a[7] if len(a) > 7 else "none",
            path=PATH,
        )))
    elif args.delete is not None:
        print(json.dumps(delete_event(args.delete, PATH)))
    elif args.update is not None:
        if not args.json:
            print(json.dumps({"ok": False, "error": "--update requires --json PAYLOAD"}))
        else:
            print(json.dumps(update_event(args.update, json.loads(args.json), PATH)))
