from crewai import Agent
from crewai.tools import tool
intent_analyzer = Agent(
  role="Intent Analyzer", 
  goal="Determine exactly what the user is requesting and extract relevant details.", 
  backstory="""
  You are an expert at understanding user requests. 
  You identify whether a request involves calendar events, 
  todo items, reminders, schedule questions, or general conversation. 
  You extract dates, times, titles, and important details.
  """
)
data_agent = Agent(
  role="Schedule Data Retriever",
  goal="Retrieve relevant calendar events, reminders, and todo information needed to fulfill the user's request.",
  backstory="""
  You specialize in finding relevant schedule,
  calendar, reminder, and todo information. 
  You gather only the information needed for the current request.
  """
)
processing_agent = Agent(
  role="Schedule Processor", 
  goal="Generate the correct response or action based on user intent and retrieved data.", 
  backstory="""
  You convert analyzed requests and retrieved schedule information 
  into useful actions. You create events, generate todo lists, 
  suggest reminders, and answer schedule questions.
  """
)
verification_agent = Agent(
  role="Response Verifier", 
  goal="Check outputs for accuracy, completeness, and consistency.", 
  backstory="""
  You perform quality control on the work of other agents. 
  You look for missing information, logical errors, 
  and incomplete responses before they are returned to the user.
  """
)

planner_agent = Agent(
    role="Calendar Planner", 
    goal="Turn a list of tasks into an optimized daily schedule",
    backstory=( 
        "You are an expert productivity assistant that organizes tasks into efficient time blocks while minimizing context switching."
    ),
    verbose=True
)

@tool("use_toml_stuff")
def use_toml_stuff(key: str, default: str = None):
    """Access or modify configuration values in a TOML file."""
    import subprocess
    result = subprocess.run(["python", "backend/tools/config_editing.py", "--key", key, "--default", str(default)], capture_output=True, text=True, cwd=str(__file__).parent.parent.parent)
    return result.stdout.strip()
