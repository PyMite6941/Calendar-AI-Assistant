# Modules for functionality
import argparse
# Modules for style
from rich.console import Console

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--get", action="store_true", help="Gets todo items")
parser.add_argument("--add", nargs=2, metavar=('TITLE', 'DESCRIPTION'), help="Adds a todo item")
parser.add_argument("--delete", metavar='ID', help="Deletes a todo item by ID")
parser.add_argument("--path", default="backend/storage/todos.txt", help="Path to the todo file")
args = parser.parse_args()

def get_todos():
    with open(args.path, "r") as file:
        return file.read()
    
def add_todo(title, description):
    with open(args.path, "a") as file:
        file.write(f"{title}: {description}\n")
    return f"Added todo: {title}"

def delete_todo(todo_id):
    with open(args.path, "r") as file:
        todos = file.readlines()
    if 0 <= int(todo_id) < len(todos):
        deleted = todos.pop(int(todo_id))
        with open(args.path, "w") as file:
            file.writelines(todos)
        return f"Deleted todo: {deleted.strip()}"
    else:
        return "Invalid ID"
    
if args.get:
    console.print(get_todos())

if args.add:
    title, description = args.add
    console.print(add_todo(title, description))

if args.delete:
    console.print(delete_todo(args.delete))