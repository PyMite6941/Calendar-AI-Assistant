# Modules for functionality
import argparse
import shutil
from pathlib import Path
# Modules for styling
import questionary
from rich.console import Console
from rich.tree import Tree

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--path", default=".", help="Path to the directory containing cache folders")
args = parser.parse_args()
root = Path(args.path).resolve()

caches = [p for p in root.rglob("__pycache__") if p.exists()]

if args.path:
    if not caches:
        console.print("[yellow]No __pycache__ folders found.[/]")
    else:
        tree = Tree(f"[bold]{root.name}[/]")
        nodes = {root: tree}

        for cache in sorted(caches):
            parent = cache.parent
            if parent not in nodes:
                nodes[parent] = tree.add(f"[dim]{parent.relative_to(root)}[/]")
            nodes[parent].add(f"[red]__pycache__[/]")

        console.print(tree)
        console.print(f"\nFound [bold red]{len(caches)}[/] cache folder(s).\n")

        if questionary.confirm("Remove all?").ask():
            removed = 0
            for cache in caches:
                if cache.exists():
                    shutil.rmtree(cache)
                    removed += 1
            console.print(f"[bold green]Done — {removed} cache folder(s) removed.[/]")
        else:
            console.print("[dim]Cancelled.[/]")
