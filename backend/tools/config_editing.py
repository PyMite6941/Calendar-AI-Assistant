import argparse
import tomlkit
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _ROOT / "backend/storage/configs.toml"


def read_config(path: Path = _DEFAULT_PATH) -> tomlkit.TOMLDocument:
    try:
        with open(path, "r") as f:
            return tomlkit.load(f)
    except FileNotFoundError:
        return tomlkit.document()


def write_config(config, path: Path = _DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        tomlkit.dump(config, f)


def get_config_value(key: str, default=None, path: Path = _DEFAULT_PATH):
    return read_config(path).get(key, default)


def set_config_value(key: str, value: str, path: Path = _DEFAULT_PATH) -> None:
    config = read_config(path)
    config[key] = value
    write_config(config, path)


if __name__ == "__main__":
    from rich.console import Console
    console = Console()

    parser = argparse.ArgumentParser()
    parser.add_argument("--key",     default=None)
    parser.add_argument("--set",     metavar="VALUE", default=None)
    parser.add_argument("--default", default=None)
    parser.add_argument("--read",    action="store_true")
    parser.add_argument("--delete",  metavar="KEY", default=None)
    parser.add_argument("--path",    default=str(_DEFAULT_PATH))
    args = parser.parse_args()
    PATH = Path(args.path)

    if args.read:
        print(tomlkit.dumps(read_config(PATH)))
    elif args.delete:
        config = read_config(PATH)
        if args.delete in config:
            del config[args.delete]
            write_config(config, PATH)
            console.print(f"[bold green]'{args.delete}' deleted.[/]")
        else:
            console.print(f"[bold red]'{args.delete}' not found.[/]")
    elif args.key and args.set is not None:
        set_config_value(args.key, args.set, PATH)
        console.print(f"[bold green]'{args.key}' set to '{args.set}'.[/]")
    elif args.key:
        config = read_config(PATH)
        print(config.get(args.key, args.default))
