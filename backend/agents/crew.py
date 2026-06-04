from crewai import Crew

from .agents import (
    intent_analyzer, 
    data_agent, 
    processing_agent, 
    verification_agent
)

from .tasks import (
    analyze_request_task,
    retrieve_data_task,
    process_request_task,
    verify_response_task
)

calendar_crew = Crew(
    agents=[
        intent_analyzer,
        data_agent,
        processing_agent,
        verification_agent
    ],
    tasks=[
        analyze_request_task,
        retrieve_data_task,
        process_request_task,
        verify_response_task
    ],
    verbose=True
)