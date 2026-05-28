# Modules for functionality
import subprocess
import sys
# Modules for styling
from rich.console import Console
from rich.panel import Panel
import questionary

console = Console()
console.print(Panel.fit("Welcome to the Calendar AI Assistant!", title="Calendar AI Assistant", title_align="center", border_style="blue", padding=(1, 2)))
choice = questionary.select(
    "How do you want to run the Calendar AI Assistant?",
    choices=[
        "Run in CLI",
        "Run in Streamlit",
        "Install necessary packages",
        "Exit",
    ],
    pointer='>'
).ask()
if choice == "Run in CLI":
    subprocess.run(["python","frontend/cli/cli.py"],verbose=True)
elif choice == "Run in Streamlit":
    subprocess.run(["streamlit","run","frontend/streamlit/Home.py"],verbose=True)
elif choice == "Install necessary packages":
    os = sys.platform
    if os.startswith("win"):
        subprocess.run(["bash install.sh"],verbose=True)
    elif os.startswith("linux") or os.startswith("darwin"):
        subprocess.run(["chmod","+x","install.sh"],verbose=True)
        subprocess.run(["./install.sh"],verbose=True)
    else:
        console.print("[red]Unsupported operating system. Please install the necessary packages manually.[/red]")
else:
    console.print("[cyan]Goodbye![/cyan]")
    sys.exit()