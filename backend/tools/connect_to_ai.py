# Modules for functionality
import argparse
import subprocess
# Modules to process AI interactions
from openai import OpenAI
# Modules for styling
from rich.console import Console

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument("--model", help="AI model to use (e.g., gpt-3.5-turbo, gpt-4)")
parser.add_argument("--provider", help="AI provider (e.g., openai)")
parser.add_argument("--ask", metavar="QUESTION", help="Asks a question to the AI assistant")
args = parser.parse_args()

urls = {
    "gemini": "https://api.gemini.com/v1/chat/completions",
    "groq": "https://api.groq.com/v1/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "ollama": "http://localhost:11434/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}

def get_api_key(model):
    try:
        result = subprocess.run(["python", "backend/tools/config_editing.py", "--read"], capture_output=True, text=True)
        config = eval(result.stdout)
        return config.get("api_key", "")
    except Exception as e:
        console.print(f"[bold red]Error retrieving API key: {e}[/]")
        return ""

if args.ask and args.model:
    try:
        client = OpenAI(base_url=urls.get(args.provider, urls["ollama"]),api_key=get_api_key(args.model))
        response = client.chat.completions.create(model=args.model, messages=[{"role": "user", "content": args.ask}])
    except Exception as e:
        console.print(f"[bold red]Error initializing AI client: {e}[/]")
        exit(1)