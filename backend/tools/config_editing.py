# Modules for functionality
import argparse
import tomlkit
# Modules for style
from rich.console import Console

console = Console()

parser = argparse.ArgumentParser()
parser.add_argument("--read", action="store_true", help="Reads the config file")
parser.add_argument("--set", nargs=2, metavar=('KEY', 'VALUE'), help="Sets a value in the config file")
parser.add_argument("--delete", metavar='KEY', help="Deletes a key from the config file")
parser.add_argument("--path", default="backend/storage/configs.toml", help="Path to the config file")
args = parser.parse_args()

def read_toml(path="backend/storage/configs.toml"):
    try:
        with open(path,'r') as file:
            return tomlkit.load(file)
    except FileNotFoundError:
        return {}

def edit_toml(key, value, path="backend/storage/configs.toml"):
    try:
        config = read_toml(path)
        config[key] = value
        with open(path,'w') as file:
            tomlkit.dump(config, file)
    except FileNotFoundError:
        config = {key: value}
        with open(path,'w') as file:
            tomlkit.dump(config, file)
    return f"[bold green]Key '{key}' set to '{value}' successfully.[/]" if args.set else f"[bold red]Failed to set key '{key}'.[/]"

if args.read:
    console.print(read_toml(args.path))

if args.set:
    key,value = args.set
    console.print(edit_toml(key, value, args.path))

if args.delete:
    key = args.delete
    config = read_toml(args.path)
    if key in config:
        del config[key]
        with open(args.path, 'w') as file:
            tomlkit.dump(config, file)
    console.print(f"[bold green]Key '{key}' deleted successfully.[/]" if key in config else f"[bold red]Key '{key}' not found.[/]")