import argparse
import tomllib
from pathlib import Path

from openai import OpenAI
from rich.console import Console

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--ask", metavar="QUESTION", required=True, help="Question to ask the AI")
parser.add_argument("--provider", default=None, help="Override provider (groq, gemini, mistral, ollama)")
args = parser.parse_args()

_ROOT = Path(__file__).resolve().parents[2]

with open(_ROOT / "backend/storage/secrets.toml", "rb") as f:
    secrets = tomllib.load(f)

PROVIDERS = {
    "groq":    ("https://api.groq.com/openai/v1", secrets["apis"].get("groq_api", ""), "llama-3.1-8b-instant"),
    "gemini":  ("https://generativelanguage.googleapis.com/v1beta/openai/", secrets["apis"].get("gemini_api", ""), "gemini-2.0-flash"),
    "mistral": ("https://api.mistral.ai/v1", secrets["apis"].get("mistral_api", ""), "mistral-small-latest"),
    "ollama":  ("http://localhost:11434/v1", "ollama", "mistral"),
}

provider = (args.provider or secrets["apis"].get("api_provider", "ollama")).lower()

if provider not in PROVIDERS:
    console.print(f"[bold red]Unknown provider '{provider}'. Choose from: {', '.join(PROVIDERS)}[/]")
    exit(1)

base_url, api_key, model = PROVIDERS[provider]

if not api_key and provider != "ollama":
    console.print(f"[bold red]No API key set for '{provider}' in secrets.toml.[/]")
    exit(1)

try:
    client = OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": args.ask}],
    )
    print(response.choices[0].message.content)
except Exception as e:
    console.print(f"[bold red]Error: {e}[/]")
    exit(1)
