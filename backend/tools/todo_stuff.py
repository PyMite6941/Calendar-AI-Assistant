import argparse
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _ROOT / "backend/storage/todos.json"

parser = argparse.ArgumentParser()
parser.add_argument("--get",    action="store_true", help="Get all todo items")
parser.add_argument("--add",    nargs="+", metavar="ARG", help="Add: TITLE DESCRIPTION [priority] [due_date] [status] [tags] [notes]")
parser.add_argument("--delete", metavar="ID", type=int, help="Delete by index")
parser.add_argument("--update", metavar="ID", type=int, help="Update by index (requires --json or field flags)")
parser.add_argument("--json",   metavar="PAYLOAD", help="JSON object of fields to update (used with --update)")
parser.add_argument("--path",   default=str(_DEFAULT_PATH), help="Path to the todo file")
args = parser.parse_args()

PATH = Path(args.path)

_DEFAULTS = {
    "title":       "",
    "description": "",
    "priority":    "medium",
    "due_date":    "",
    "status":      "pending",
    "tags":        [],
    "notes":       "",
}

def _coerce(item: dict) -> dict:
    return {**_DEFAULTS, **item}

def get_todos():
    try:
        with open(PATH, "r") as f:
            return [_coerce(t) for t in json.load(f)]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_todos(todos):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PATH, "w") as f:
        json.dump(todos, f, indent=2)

if args.get:
    print(json.dumps(get_todos()))

elif args.add:
    a = args.add
    todo = {
        "title":       a[0] if len(a) > 0 else "",
        "description": a[1] if len(a) > 1 else "",
        "priority":    a[2] if len(a) > 2 else "medium",
        "due_date":    a[3] if len(a) > 3 else "",
        "status":      a[4] if len(a) > 4 else "pending",
        "tags":        json.loads(a[5]) if len(a) > 5 else [],
        "notes":       a[6] if len(a) > 6 else "",
    }
    todos = get_todos()
    todos.append(todo)
    save_todos(todos)
    print(json.dumps({"ok": True, "action": "added", "todo": todo}))

elif args.delete is not None:
    todos = get_todos()
    if 0 <= args.delete < len(todos):
        removed = todos.pop(args.delete)
        save_todos(todos)
        print(json.dumps({"ok": True, "action": "deleted", "todo": removed}))
    else:
        print(json.dumps({"ok": False, "error": f"Index {args.delete} out of range (0–{len(todos) - 1})"}))

elif args.update is not None:
    todos = get_todos()
    if not (0 <= args.update < len(todos)):
        print(json.dumps({"ok": False, "error": f"Index {args.update} out of range (0–{len(todos) - 1})"}))
    elif not args.json:
        print(json.dumps({"ok": False, "error": "--update requires --json PAYLOAD"}))
    else:
        patch = json.loads(args.json)
        todos[args.update] = {**todos[args.update], **patch}
        save_todos(todos)
        print(json.dumps({"ok": True, "action": "updated", "todo": todos[args.update]}))
