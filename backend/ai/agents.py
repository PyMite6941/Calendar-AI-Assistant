intent_analyzer = Agent(
  role="Intent Analyzer", 
  goal="Determine exactly what the user is requesting and extract relevant details.", 
  backstory="""
  You are an expert at understanding user requests. 
  You identify whether a request involves calendar events, 
  todo items, reminders, schedule questions, or general conversation. 
  You extract dates, times, titles, and important details.
  """)
data_agent = Agent(
  role="Schedule Data Retriever"
  goal="Find all information needed to fulfill the user's request."
  backstory="""
  You specialize in finding relevant schedule,
  calendar, reminder, and todo information. 
  You gather only the information needed for the current request.
  """
)
processing_age
verification_agent
