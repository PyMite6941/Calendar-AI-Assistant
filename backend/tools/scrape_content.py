import argparse
import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True, help="URL to scrape")
parser.add_argument("--output", default=None, help="Optional path to save scraped text as JSON")
args = parser.parse_args()

_ROOT = Path(__file__).resolve().parents[2]

def scrape(url: str) -> dict:
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title else ""
        text = " ".join(soup.get_text(separator=" ").split())

        return {"url": url, "title": title, "content": text, "error": None}
    except Exception as e:
        return {"url": url, "title": "", "content": "", "error": str(e)}


result = scrape(args.url)

if result["error"]:
    console.print(f"[bold red]Failed to scrape {args.url}: {result['error']}[/]")
else:
    print(json.dumps(result))
    if args.output:
        output_path = Path(args.output) if Path(args.output).is_absolute() else _ROOT / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2))
        console.print(f"[green]Saved to {output_path}[/]")
