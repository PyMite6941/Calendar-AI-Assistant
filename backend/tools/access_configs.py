import argparse
import tomllib
import tomli_w
from rich.console import Console

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--key", required=True, help="Configuration key")
parser.add_argument("--get", action="store_true", help="Get the value for --key")
parser.add_argument("--set", metavar="VALUE", help="Set --key to this value")
parser.add_argument("--default", default=None, help="Default value if key not found (used with --get)")
parser.add_argument("--path", default="backend/storage/configs.toml", help="Path to config file")
args = parser.parse_args()

def get_config(key, default=None):
    try:
        with open(args.path, "rb") as f:
            configs = tomllib.load(f)
        return configs.get(key, default)
    except FileNotFoundError:
        return default

def set_config(key, value):
    try:
        with open(args.path, "rb") as f:
            configs = tomllib.load(f)
    except FileNotFoundError:
        configs = {}
    configs[key] = value
    with open(args.path, "wb") as f:
        tomli_w.dump(configs, f)
    return f"[bold green]'{key}' set to '{value}'.[/]"

if args.set:
    console.print(set_config(args.key, args.set))
elif args.get or args.key:
    print(get_config(args.key, args.default))
