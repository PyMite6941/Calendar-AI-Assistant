import json
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from crewai import Crew, Task, Process
from backend.agents.agents import planner_agent

_PLAN_PATH = _ROOT / "backend/storage/daily_plan.json"


def run_planner() -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")
    task = Task(
        description=f"""
Today is {today}.

Use get_calendar_events and get_todos to read the user's full schedule and task list.
Then produce an optimised, time-blocked daily plan for today that:
- Treats all existing calendar events as hard, immovable blocks
- Batches similar tasks together to minimise context switching
- Leaves 10-minute buffer gaps between blocks
- Covers the working day from the earliest existing event (or 9:00 AM) to 6:00 PM
- Schedules todo items without fixed times into available gaps, ordered by priority

Format the plan as:
  HH:MM - HH:MM  |  Activity
  ...
Then add a short Rationale paragraph (3-5 sentences) explaining the ordering.
""",
        expected_output=(
            "A formatted time-blocked plan for today (HH:MM - HH:MM | Activity rows), "
            "followed by a Rationale paragraph explaining batching and ordering decisions."
        ),
        agent=planner_agent,
    )
    crew = Crew(agents=[planner_agent], tasks=[task], process=Process.sequential, verbose=False)
    try:
        result = str(crew.kickoff()).strip()
    except Exception as exc:
        raise RuntimeError(f"Planner crew failed: {exc}") from exc

    if not result:
        raise RuntimeError("Planner returned an empty plan.")

    _PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PLAN_PATH.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(),
        "plan_date": datetime.now().strftime("%Y-%m-%d"),
        "plan_text": result,
    }, indent=2))

    return result


def get_saved_plan() -> dict:
    try:
        return json.loads(_PLAN_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


if __name__ == "__main__":
    print(run_planner())
