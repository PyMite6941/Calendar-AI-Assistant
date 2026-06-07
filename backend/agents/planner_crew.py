import json
import sys
import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from crewai import Crew, Task, Process
from backend.agents.agents import planner_agent

_PLAN_PATH = _ROOT / "backend/storage/daily_plan.json"


def _user_tz() -> tuple[str, ZoneInfo]:
    try:
        with open(_ROOT / "backend/storage/configs.toml", "rb") as f:
            tz_name = tomllib.load(f).get("timezone") or "UTC"
    except Exception:
        tz_name = "UTC"
    try:
        return tz_name, ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return "UTC", ZoneInfo("UTC")


def run_planner() -> str:
    tz_name, tz = _user_tz()
    now   = datetime.now(tz)
    today = now.strftime("%A, %B %d, %Y")
    time  = now.strftime("%H:%M")
    task = Task(
        description=f"""
Today is {today}. Timezone: {tz_name} — current local time is {time}.

Use get_calendar_events and get_google_calendar_events to read all calendar events
(local and Google Calendar). Use get_todos to read the task list.
Merge events from both sources, treating duplicates by title as the same event.

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
        "generated_at": now.isoformat(),
        "plan_date": now.strftime("%Y-%m-%d"),
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
