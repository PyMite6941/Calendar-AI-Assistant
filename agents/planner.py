from crewai import Agent

planner_agent = Agent(
    role="Calendar Planner", 
    goal="Turn a list of tasks into an optimized daily schedule",
    backstory=( 
        "You are an expert productivity assistant that organizes tasks into effecient time blocks while minimizing context switching."
    ),
    verbose=True
)