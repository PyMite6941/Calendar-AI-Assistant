import argparse
import json
from pathlib import Path

from rich.console import Console

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _ROOT / "backend/storage/todos.json"

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--get", action="store_true", help="Gets todo items")
parser.add_argument("--add", nargs=2, metavar=("TITLE", "DESCRIPTION"), help="Adds a todo item")
parser.add_argument("--delete", metavar="ID", type=int, help="Deletes a todo item by index")
parser.add_argument("--path", default=str(_DEFAULT_PATH), help="Path to the todo file")
args = parser.parse_args()

PATH = Path(args.path)

def get_todos():
    try:
        with open(PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_todos(todos):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PATH, "w") as f:
        json.dump(todos, f, indent=2)

if args.get:
    print(json.dumps(get_todos()))

if args.add:
    title, description = args.add
    todos = get_todos()
    todos.append({"title": title, "description": description})
    save_todos(todos)
    console.print(f"[bold green]Added todo: {title}[/]")

if args.delete is not None:
    todos = get_todos()
    if 0 <= args.delete < len(todos):
        removed = todos.pop(args.delete)
        save_todos(todos)
        console.print(f"[bold green]Deleted: {removed['title']}[/]")
    else:
        console.print("[bold red]Invalid ID.[/]")
