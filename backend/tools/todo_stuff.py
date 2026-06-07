import argparse
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _ROOT / "backend/storage/todos.json"

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


def get_todos(path: Path = _DEFAULT_PATH) -> list:
    try:
        with open(path, "r") as f:
            return [_coerce(t) for t in json.load(f)]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_todos(todos: list, path: Path = _DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(todos, f, indent=2)


def add_todo(title: str, description: str = "", priority: str = "medium",
             due_date: str = "", status: str = "pending",
             tags: list = None, notes: str = "",
             path: Path = _DEFAULT_PATH) -> dict:
    todo = _coerce({
        "title": title, "description": description, "priority": priority,
        "due_date": due_date, "status": status,
        "tags": tags if tags is not None else [], "notes": notes,
    })
    todos = get_todos(path)
    todos.append(todo)
    save_todos(todos, path)
    return {"ok": True, "action": "added", "todo": todo}


def delete_todo(index: int, path: Path = _DEFAULT_PATH) -> dict:
    todos = get_todos(path)
    if not todos:
        return {"ok": False, "error": "No todos to delete"}
    if 0 <= index < len(todos):
        removed = todos.pop(index)
        save_todos(todos, path)
        return {"ok": True, "action": "deleted", "todo": removed}
    return {"ok": False, "error": f"Index {index} out of range (0–{len(todos) - 1})"}


def update_todo(index: int, patch: dict, path: Path = _DEFAULT_PATH) -> dict:
    todos = get_todos(path)
    if not todos:
        return {"ok": False, "error": "No todos to update"}
    if not (0 <= index < len(todos)):
        return {"ok": False, "error": f"Index {index} out of range (0–{len(todos) - 1})"}
    todos[index] = {**todos[index], **patch}
    save_todos(todos, path)
    return {"ok": True, "action": "updated", "todo": todos[index]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--get",    action="store_true")
    parser.add_argument("--add",    nargs="+", metavar="ARG")
    parser.add_argument("--delete", metavar="ID", type=int)
    parser.add_argument("--update", metavar="ID", type=int)
    parser.add_argument("--json",   metavar="PAYLOAD")
    parser.add_argument("--path",   default=str(_DEFAULT_PATH))
    args = parser.parse_args()
    PATH = Path(args.path)

    if args.get:
        print(json.dumps(get_todos(PATH)))
    elif args.add:
        a = args.add
        print(json.dumps(add_todo(
            title=a[0] if len(a) > 0 else "",
            description=a[1] if len(a) > 1 else "",
            priority=a[2] if len(a) > 2 else "medium",
            due_date=a[3] if len(a) > 3 else "",
            status=a[4] if len(a) > 4 else "pending",
            tags=json.loads(a[5]) if len(a) > 5 else [],
            notes=a[6] if len(a) > 6 else "",
            path=PATH,
        )))
    elif args.delete is not None:
        print(json.dumps(delete_todo(args.delete, PATH)))
    elif args.update is not None:
        if not args.json:
            print(json.dumps({"ok": False, "error": "--update requires --json PAYLOAD"}))
        else:
            print(json.dumps(update_todo(args.update, json.loads(args.json), PATH)))
