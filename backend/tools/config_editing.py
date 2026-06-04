import argparse
import tomlkit
from pathlib import Path
from rich.console import Console

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _ROOT / "backend/storage/configs.toml"

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--key", default=None, help="Key to get or set")
parser.add_argument("--set", metavar="VALUE", default=None, help="Set --key to this value")
parser.add_argument("--default", default=None, help="Default value if key not found")
parser.add_argument("--read", action="store_true", help="Read and print entire config file")
parser.add_argument("--delete", metavar="KEY", default=None, help="Delete a key")
parser.add_argument("--path", default=str(_DEFAULT_PATH), help="Path to the config file")
args = parser.parse_args()

PATH = Path(args.path)


def read_toml():
    try:
        with open(PATH, "r") as f:
            return tomlkit.load(f)
    except FileNotFoundError:
        return tomlkit.document()


def write_toml(config):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PATH, "w") as f:
        tomlkit.dump(config, f)


if args.read:
    print(tomlkit.dumps(read_toml()))

elif args.delete:
    config = read_toml()
    if args.delete in config:
        del config[args.delete]
        write_toml(config)
        console.print(f"[bold green]'{args.delete}' deleted.[/]")
    else:
        console.print(f"[bold red]'{args.delete}' not found.[/]")

elif args.key and args.set is not None:
    config = read_toml()
    config[args.key] = args.set
    write_toml(config)
    console.print(f"[bold green]'{args.key}' set to '{args.set}'.[/]")

elif args.key:
    config = read_toml()
    print(config.get(args.key, args.default))
