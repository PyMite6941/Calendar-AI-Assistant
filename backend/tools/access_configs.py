# Modules for functionality
import argparse
import tomllib
# Modules for styling
from rich.console import Console

console = Console()
args = argparse.ArgumentParser()
args.add_argument("--key", required=True, help="Configuration key to retrieve")
args.add_argument("--default", default=None, help="Default value if key is not found")
args.add_argument("--path", default="backend/storage/configs.toml", help="Path to the configuration file")
args = args.parse_args()

def get_config(key):
    with open(args.path, "r") as file:
        configs = tomllib.load(file)
    return configs.get(key, args.default)

def set_config(key, value):
    with open(args.path, "r") as file:
        configs = tomllib.load(file)
    configs[key] = value
    with open(args.path, "w") as file:
        tomllib.dump(configs, file)
    return f"[bold green]Configuration '{key}' set to '{value}' successfully.[/]" if args.key and args.default else "[bold red]Failed to set configuration.[/]"

if args.key and args.default:
    console.print(set_config(args.key, args.default))
elif args.key:
    console.print(get_config(args.key))