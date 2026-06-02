from crewai import Task
from .agents import (
  intent_analyzer, 
  data_agent, 
  processing_agent, 
  verification_agent
)
analyze_request_task = Task(
  description="""
  Analyze the user's request and determine the intent. 
  Extract any dates, times, titles, reminders, 
  and relevant scheduling information.
  """,
  expected_output="""
  A structured description of the user's intent
  and extracted details.
  """, 
  agent=intent_analyzer
)
retrieve_data_task = Task(
  description="""
  Retrieve any calendar events, reminders, 
  and todo information relevant to the request.
  """, 
  expected_output="""
  Relevant schedule, reminder, 
  and todo information.
  """, 
  agent=data_agent
)
process_request_task = Task(
  description="""
  Generate the appropriate response or action
  using the analyzed intent and retrieved data. 
  """, 
  expected_output="""
  A completed response, recommendation, 
  calendar action, reminder, or todo action.
  """, 
  agent=processing_agent
)
verify_response_task = Task(
  description="""
  Review the generated response for accuracy, 
  completeness, and consistency. 
  """, 
  expected_output="""
  A verified response that is accurate, 
  complete, consistent, and ready to return to the user.
  """, 
  agent=verification_agent
)

from crewai import Task
from agents.planner import planner_agent

schedule_task = Task(
    description=(
        "Create a realistic daily schedule for a student with:\n"
        "- 2 hours studying\n"
        "- 1 hour exercise\n" \
        "- 3 hours project work\n"
        "- breaks and meals included\n"
        "Optimize for focus and energy levels."
    ),
    agent=planner_agent,
    expected_output="A structured hourly schedule for the day."
)