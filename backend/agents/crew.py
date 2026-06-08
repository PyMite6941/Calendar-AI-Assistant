import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from crewai import Crew, Process

from .agents import (
    intent_analyzer,
    data_agent,
    processing_agent,
    verification_agent,
)
from .tasks import (
    analyze_request_task,
    retrieve_data_task,
    process_request_task,
    verify_response_task,
)

_ROOT = Path(__file__).resolve().parents[2]

calendar_crew = Crew(
    agents=[
        intent_analyzer,
        data_agent,
        processing_agent,
        verification_agent,
    ],
    tasks=[
        analyze_request_task,
        retrieve_data_task,
        process_request_task,
        verify_response_task,
    ],
    process=Process.sequential,
    verbose=False,
)


def _build_kickoff_context() -> dict:
    """Return dynamic date/timezone/user context fresh for each crew run."""
    try:
        with open(_ROOT / "backend/storage/configs.toml", "rb") as f:
            configs = tomllib.load(f)
    except Exception:
        configs = {}

    tz_name = configs.get("timezone") or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
        tz_name = "UTC"

    now = datetime.now(tz)
    today  = now.strftime("%A, %B %d, %Y")
    tz_ctx = f"Timezone: {tz_name} — current local time is {now.strftime('%H:%M')}."

    user_parts = []
    user_name = (configs.get("user_name") or "").strip()
    if user_name:
        user_parts.append(f"The user's name is {user_name}.")
    notif = (configs.get("notification_preferences") or "").strip()
    if notif:
        user_parts.append(f"Notification preferences: {notif}.")
    wh_start = (configs.get("working_hours_start") or "").strip()
    wh_end   = (configs.get("working_hours_end") or "").strip()
    if wh_start and wh_end:
        user_parts.append(f"Working hours: {wh_start} to {wh_end}.")

    return {
        "today":    today,
        "tz_ctx":   tz_ctx,
        "user_ctx": "  ".join(user_parts),
    }


def run_calendar_assistant(user_request: str) -> str:
    ctx = _build_kickoff_context()
    result = calendar_crew.kickoff(inputs={"user_request": user_request, **ctx})
    return str(result)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ask", required=True, help="User request to process through the crew")
    args = parser.parse_args()
    print(run_calendar_assistant(args.ask))
