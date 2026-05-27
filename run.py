# For functionality
import subprocess
# For styling
from rich.console import Console
from rich.panel import Panel
import questionary

console = Console()
choice = questionary.Choice(
    "",
    choices=(
        questionary.Choice("Run in CLI"),
        questionary.Choice("Run in Streamlit"),
    ),
    pointer='>'
)
if choice == "Run in CLI":
    subprocess.run(["python","frontend/cli/cli.py"],verbose=True)
elif choice == "Run in Streamlit":
    subprocess.run(["streamlit","run","frontend/streamlit/Home.py"],verbose=True)