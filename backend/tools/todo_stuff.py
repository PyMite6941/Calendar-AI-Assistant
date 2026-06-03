import argparse
from rich.console import Console

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--get", action="store_true", help="Gets todo items")
parser.add_argument("--add", nargs=2, metavar=("TITLE", "DESCRIPTION"), help="Adds a todo item")
parser.add_argument("--delete", metavar="ID", help="Deletes a todo item by ID")
parser.add_argument("--path", default="backend/storage/todos.txt", help="Path to the todo file")
args = parser.parse_args()

def get_todos():
    try:
        with open(args.path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def add_todo(title, description):
    with open(args.path, "a") as f:
        f.write(f"{title}: {description}\n")
    return f"[bold green]Added todo: {title}[/]"

def delete_todo(todo_id):
    try:
        with open(args.path, "r") as f:
            todos = f.readlines()
        idx = int(todo_id)
        if 0 <= idx < len(todos):
            deleted = todos.pop(idx)
            with open(args.path, "w") as f:
                f.writelines(todos)
            return f"[bold green]Deleted: {deleted.strip()}[/]"
        return "[bold red]Invalid ID.[/]"
    except FileNotFoundError:
        return "[bold red]No todos found.[/]"

if args.get:
    console.print(get_todos())

if args.add:
    console.print(add_todo(*args.add))

if args.delete:
    console.print(delete_todo(args.delete))
