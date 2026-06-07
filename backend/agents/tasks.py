from datetime import datetime
from crewai import Task

from .agents import (
    intent_analyzer,
    data_agent,
    processing_agent,
    verification_agent,
)

_TODAY = datetime.now().strftime("%A, %B %d, %Y")

analyze_request_task = Task(
    description=f"""
Today is {_TODAY}.

Analyse the following user request:

{{user_request}}

Identify the intent (add event, add todo, query schedule, update item, delete item, general chat).
Extract all relevant details: dates, times, titles, locations, priorities, due dates, recurrence.
Convert any relative dates (e.g. "tomorrow", "next Monday", "in four days") to absolute dates
based on today's date above.
""",
    expected_output=(
        "A structured breakdown with: (1) intent type (add/update/delete/query/chat), "
        "(2) entity fields (title, start, end, location, priority, due_date, recurrence, etc.), "
        "(3) all relative dates converted to absolute YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS, "
        "(4) any stated assumptions where the message was ambiguous."
    ),
    agent=intent_analyzer,
)

retrieve_data_task = Task(
    description=f"""
Today is {_TODAY}.

The original user request was: {{user_request}}

Using the intent analysis from the previous step, retrieve all calendar events and todo items
that are relevant to fulfilling the request.
Use get_calendar_events and get_todos tools to fetch current data.
Use get_config to read user preferences such as user_name or timezone if helpful.
Only retrieve what is needed — do not dump everything if the request is narrow.
""",
    expected_output=(
        "The retrieved events and/or todos as structured data, with each item's index clearly stated "
        "so the processing agent can reference it directly. If nothing relevant exists, state that explicitly."
    ),
    agent=data_agent,
    context=[analyze_request_task],
)

process_request_task = Task(
    description=f"""
Today is {_TODAY}.

The original user request was: {{user_request}}

Using the intent analysis and the retrieved data from the previous steps, carry out the appropriate action:
- If adding an event: call add_calendar_event with all relevant fields.
- If adding a todo: call add_todo with title, priority, due_date, and notes where available.
- If updating: call update_calendar_event or update_todo with the correct index and patch JSON.
- If deleting: call delete_calendar_event or delete_todo with the correct index.
- If answering a question: compose a clear, concise answer from the retrieved data.

Always use the resolved absolute dates from the analysis step.
""",
    expected_output=(
        "One of: (a) confirmation that the write action was executed (tool output included), "
        "(b) a clear, factual answer to the user's question based on the retrieved data. "
        "Must include the tool's return value for any write actions."
    ),
    agent=processing_agent,
    context=[analyze_request_task, retrieve_data_task],
)

verify_response_task = Task(
    description=f"""
Today is {_TODAY}.

The original user request was: {{user_request}}

Review the output from the processing step:
- If an action was taken (add/update/delete), verify it was correct and complete.
- If a question was answered, verify the answer is accurate based on the retrieved data.
- Check for missing fields, wrong dates, or logical errors.
- If everything is correct, return the final response to the user.
- If something is wrong, describe what needs to be corrected.
""",
    expected_output=(
        "A single, final message in warm second-person language ('Your event has been added', "
        "'You have 3 todos due this week') that is accurate, concise, and ready to display verbatim. "
        "If something was wrong, a clear description of the error instead."
    ),
    agent=verification_agent,
    context=[process_request_task],
)
