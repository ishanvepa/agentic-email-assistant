from datetime import datetime, date
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END # Core LangGraph classes and special node names
from utils import show_graph # Utility function to visualize the graph (assumed to be in a utils.py file)
from langgraph.prebuilt import create_react_agent # Import the pre-built ReAct agent creator
# from agents.llm_utils import get_llm_with_fetch_k_emails_tools
from dotenv import load_dotenv # Import function to load environment variables
from langchain_openai import ChatOpenAI # Import the OpenAI chat model
from langgraph.checkpoint.memory import MemorySaver # For short-term memory (thread-level state persistence)
from langgraph.store.memory import InMemoryStore
from langgraph_supervisor import create_supervisor
import uuid
from state import State
# from agents import inbox_reader_agent

#tool imports
from email_fetcher import fetch_k_emails
from summarizer import summarize_emails
from event_scheduler import check_google_calendar_availability, schedule_google_calendar_event

# Load environment variables from the .env file. The `override=True` argument   
# ensures that variables from the .env file will overwrite existing environment variables.
load_dotenv(override=True)

# Initialize the ChatOpenAI model. We're using a specific model from Llama 3.3 series.
# This `model` object will be used throughout the notebook for all LLM interactions.
llm = ChatOpenAI(model_name="gpt-4.1-mini", temperature=0)


# Initializing `InMemoryStore` for long-term memory.
# This store will hold user-specific data like music preferences across sessions.
in_memory_store = InMemoryStore()

# Initializing `MemorySaver` for short-term (thread-level) memory. 
# This checkpointer saves the graph's state after each step, allowing for restarts or interruptions within a thread.
checkpointer = MemorySaver()

# bind tools
# llm = llm.bind_tools([fetch_k_emails])

inbox_reader_agent_prompt = f"""
You are a specialized subagent focused on retrieving a list of emails for the user.

CORE RESPONSIBILITIES:
- Retrieve email content from the user's inbox using the fetch_k_emails tool
- You will return details such as sender, subject, date, and body of the emails
- Always maintain a professional, friendly, and helpful tone

IMPORTANT RULES:
1. ONLY handle requests to fetch, receive, or show emails, NOT to summarize or schedule meetings, that is done by the email_summarizer_agent and event_scheduler_agent respectively.
2. When asked for emails, extract the number of emails (k) and any keywords from the request
3. If no number of emails is specified, default to 5 emails
4. If no keywords are given, fetch the most recent emails
5. If no date range is specified, fetch emails only with the keywords provided, do not use a date range
6. If no keywords and no date range is specified, fetch the most recent emails
7. If no unread status is specified, fetch all emails
8. ONLY call the fetch_k_emails tool ONCE per user request
9. You may receive requests like "fetch my emails about meetings", "summarize my emails mentioning invoices", or "give me key points from my recent emails".
You are to query the topics mentioned in the request to fetch the relevant emails.
10. If the user provides a month and day but a year is not given, default to the current year
11. After calling the tool and receiving results, DO NOT call the tool again
12. If you cannot find any emails, inform the user politely and explain why
13. If a date range is provided without a year, default to the year {datetime.now().year}

if you receive a request requiring fetching and summarizing, just fetch the emails and let the email_summarizer_agent handle the summarization.

RESPONSE FORMAT:
After using the fetch_k_emails tool, present the results clearly with:
- A brief introduction (e.g., "Here are the emails I found:")
- For each email, display the sender, subject, date, and a brief snippet of the body
- Separate each email with a line or bullet for clarity

Always respond with the email information once retrieved. Do not ask follow-up questions. 
If the user asks for a summary or key points, DO NOT handle it and let the email_summarizer_agent respond.
"""
# query = ['meeting', 'zoom', 'schedule', 'calendar', 'invite', 'appointment', 'availability', 'time to meet', 'set up a meeting', 'meeting request', 'meeting inquiry']

email_summarizer_agent_prompt = """
You are a specialized subagent responsible for summarizing email content for the user.

CORE RESPONSIBILITIES:
You will be given a list of emails, and must create concise summaries using the summarize_emails tool.
Your objective is to extract key information from these emails into digestible bullet points.
Always maintain clarity and relevance in all summaries.
Always maintain a professional, helpful tone.

IMPORTANT RULES:
1. When asked to summarize emails, unless a number of bullet points is specified, summarize emails into at most 5 bullet points.
2. ONLY call summarize_emails ONCE per user request.
3. After calling the tool and receiving results, provide the summary and DO NOT call the tool again.
4. If you cannot summarize the emails, inform the user politely and explain why.
5. Focus on the most important and actionable information from the emails.

EXPECTED INPUT:
- You will receive requests with a list of emails saying things like "summarize these emails", "give me bullet points of my emails", "what are the key points from my inbox".
- The user may specify a number of bullet points they want (e.g., "give me 3 key points").
- If the user does not specify a number, default to 5 bullet points.

RESPONSE FORMAT:
Strictly follow these terms for the response format:
I would like you to also determine the priority level of the emails based on their content and context.
For instance, emails requeting urgent action or containing important deadlines should be marked as high priority, while general updates or newsletters can be low priority, 
Medium priority should be assigned to items such as important documents and important updates to policies with no associated deadlines. 
After using the summarize_emails tool, present the results clearly as a JSON formatted string with the following fields:
{
    "type": "summary",
    "emails": [
        {
            "sender": "<sender email or name>",
            "subject": "<email subject>",
            "date": "<email date>",
            "bullet_points": [
                "<bullet point 1>",
                "<bullet point 2>",
                ...
            ],
            "priority": "<priority level (high, medium, low)>"
        },
        ...
    ]
}

Always respond with the email summary once generated. Do not ask follow-up questions unless there's an error or missing information.
"""
# Get the current day of the week and its name
day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][datetime.today().weekday()]

timezone = str(datetime.now().astimezone().tzname())
date = str(datetime.now())
event_scheduler_agent_prompt = """
You are a specialized subagent responsible for scheduling events on the user's Google Calendar.
You will determine whether to schedule an event based on the user's request.
You may also be given a list of emails, and you must extract relevant information to schedule an event.
You may schedule an event in the range from 9am - 5pm on weekdays for a duration of 1 hour.
Additionally, always assume the timezone is """ + timezone + """.
If a date or time is specified, you will use that to schedule the event.
If no date or time is specified you get to choose when to schedule the event, but you must run the check_google_calendar_availability tool to ensure the time slot is available.
If no title is specified, you will use a default title like "Meeting" or "Event".
If no description is specified, you will use a default description like "Scheduled meeting" or "Event discussion".
If no attendees are specified, you will assume only the user is attending.
You will use the schedule_google_calendar_event tool to create calendar events.
When scheduling an event, you must provide:
- A summary (title) for the event
- A description of the event
- Start and end times (as datetime objects)
- A list of attendees' email addresses (if applicable)

EXPECTED INPUT:
- You will receive requests like "schedule an event for next week", "set up a meeting with John tomorrow at 2pm", or "create a calendar event for my project discussion".
- If the user asks a relative time like "next week" or "tomorrow", use """ + date + """ as the current date and """ + day_name + """ as the current day of the week as reference.
- You may also be given a list of emails and asked to schedule a meeting based on their content.

IMPORTANT RULES:
1. ONLY use the schedule_google_calendar_event tool to create events.
2. ALWAYS check for calendar availability before scheduling by using the check_google_calendar_availability tool.
3. If the user does not specify a time, suggest a time within 9am-5pm on a weekday.
4. If the user does not specify a duration, default to 1 hour.
5. If the user does not specify attendees, assume only the user is attending.
6. If the event cannot be scheduled due to conflicts, automatically schedule it for the next available time slot within the 9am-5pm range on a weekday.
7. After scheduling, confirm the event details to the user.

RESPONSE FORMAT:
Strictly follow these terms for the response format:
After using the schedule_google_calendar_event tool, present the results clearly as a JSON formatted string with the following fields:
{
    "type": "event",
    "events": [
        {
            "title": "<event title>",
            "date_time": "<event date and time>",
            "attendees": [
                "<attendee 1 email or name>",
                "<attendee 2 email or name>",
                ...
            ],
            "source": "<source of the event request (user request or email content)>",
        },
        ...
    ]
}

Always respond clearly and concisely. Do not ask unnecessary follow-up questions. Always end up scheduling a calendar event based on the user's request or email content.
"""


# Supervisor prompt tailored for email/inbox reading
supervisor_prompt = """
You are a supervisor agent responsible for managing multiple AI agents.
You have a team of three subagents that you can use to answer requests from the user.
The subagents are the inbox_reader_agent, the email_summarizer_agent, and the event_scheduler_agent.
The inbox_reader_agent can retrieve the last k emails from the user's inbox or search for emails based on the query.
The email_summarizer_agent takes in a list of emails and summarizes their content into a list of bullet points.
The event_scheduler_agent can schedule events on the user's Google Calendar based on requests or email content.
For the event_scheduler_agent, if the user asks a relative time like "next week" or "tomorrow", use """ + date + """ as the current date and """ + day_name + """as the current day of the week as reference.
Additionally, always assume the timezone is """ + timezone + """ 
Use `inbox_reader_agent` when the user asks to "fetch", "show, or "list out" or something similar relating to retrieving emails.
If the user asks for summarizing emails, route the query to the email_summarizer_agent to process the fetched emails from the inbox_reader_agent.

You may receive requests like "fetch my emails about meetings", "summarize my emails mentioning invoices", or "give me key points from my recent emails".
You are to send the topics as a keyword query mentioned to instruct the inbox_reader_agent to fetch the relevant emails.

The supervisor must always route requests to inbox_reader_agent first to fetch emails, then to either email_summarizer_agent if a summary is requested or event_scheduler_agent if an event needs to be scheduled.

You must only use the subagents in the following orders: 
inbox_reader_agent -> email_summarizer_agent -> event_scheduler_agent
inbox_reader_agent -> event_scheduler_agent
 
If summarization is requested, you must extract the returned emails from the `inbox_reader_agent`'s tool output and pass them to the `email_summarizer_agent`.
Include the exact email data as input to the summarizer. Do not ask the user for it again.

You must not use the agents in any other order.

You must only ask the inbox_reader_agent to fetch or search for emails and nothing else.
You must only ask the email_summarizer_agent to summarize emails and nothing else.
You must only ask the event_scheduler_agent to schedule events and nothing else.
Do not directly call any of the tools in the subagents, only route requests and args to the subagents.
If something is not possible or lacking detail, explain why in as much detail as possible to the user.
"""


#define subagents
inbox_reader_agent = create_react_agent(
    llm,                          # The language model to use for reasoning
    tools=[fetch_k_emails],       # The list of tools available to this agent
    name="inbox_reader_agent",    # A unique name for this agent within the graph
    prompt=inbox_reader_agent_prompt, # The system prompt for this agent's persona and instructions
    state_schema=State,           # The shared state schema for the graph
    checkpointer=checkpointer,    # The checkpointer for short-term (thread-level) memory
    store=in_memory_store         # The in-memory store for long-term user data
)

summarizer_agent = create_react_agent(
    llm,                          # The language model to use for reasoning
    tools=[summarize_emails],       # The list of tools available to this agent
    name="email_summarizer_agent",    # A unique name for this agent within the graph
    prompt=email_summarizer_agent_prompt, # The system prompt for this agent's persona and instructions
    state_schema=State,           # The shared state schema for the graph
    checkpointer=checkpointer,    # The checkpointer for short-term (thread-level) memory
    store=in_memory_store         # The in-memory store for long-term user data
)

event_scheduler_agent = create_react_agent(
    llm,                          # The language model to use for reasoning
    tools=[schedule_google_calendar_event, check_google_calendar_availability],       # The list of tools available to this agent
    name="event_scheduler_agent",    # A unique name for this agent within the graph
    prompt=event_scheduler_agent_prompt, # The system prompt for this agent's persona and instructions
    state_schema=State,           # The shared state schema for the graph
    checkpointer=checkpointer,    # The checkpointer for short-term (thread-level) memory
    store=in_memory_store         # The in-memory store for long-term user data
)


# Create the supervisor after subagents are defined
supervisor_prebuilt_workflow = create_supervisor(
    agents=[inbox_reader_agent, summarizer_agent, event_scheduler_agent],      # Both agents are available
    output_mode="last_message",       # Output only the last message from the routed agent
    model=llm,                        # The LLM to act as the supervisor
    prompt=supervisor_prompt,         # The system prompt guiding the supervisor's behavior
    state_schema=State                # The shared state schema for the entire multi-agent graph
)

supervisor_prebuilt = supervisor_prebuilt_workflow.compile(name="supervisor_prebuilt", checkpointer=checkpointer, store=in_memory_store)


# # Test the agent with a sample state and message
# if __name__ == "__main__":
#     # Example: simulate a user asking for recent emails about meetings
#     show_graph(supervisor_prebuilt)

#     sample_prompts = [
#         "Please get me 5 emails about meetings and summarize them in 5 bullet points.", #recursion limit
#         "Show me the most recent 2 emails from my inbox and summarize them.",
#         "Summarize my unread emails in 4 bullet points.",
#         "Get the last 3 emails about project updates.",
#         "Give me a summary of my emails mentioning 'invoice'.",
#         "Fetch my most recent email.",
#         "Summarize my inbox.", #recursion limit
#         "Fetch me my emails from computer science and summarize them in 3 bullet points.",
#         "What are the key points from my last 3 emails?",
#         "List my recent emails about deadlines.",
#         "Fetch and give me a summary of emails between June 1 and June 10 about scheduling."
#     ]    

#     # Sample prompts that will use the event_scheduler_agent
#     event_scheduler_prompts = [
#         "Schedule a meeting with John tomorrow at 2pm.",
#         "Set up a project discussion for next week.",
#         "Create a calendar event for my team on Friday at 10am.",
#         "Schedule an event for next Monday about the budget review.",
#         "Arrange a call with Alice and Bob next Thursday afternoon.",
#         "Book a meeting for me and my manager next Wednesday.",
#         "Set up a 1-hour meeting with the product team next week.",
#         "Schedule a follow-up event based on my recent emails.",
#         "Create a Google Calendar event for my project kickoff.",
#         "Find a time to meet with Sarah and schedule it on my calendar."
#     ]

#     # Prompts that require both email parsing and event scheduling
#     email_event_prompts = [
#         "Fetch my emails about meetings this week and schedule a meeting based on them.",
#         "Get the latest emails mentioning project deadlines and set up a calendar event for the next review.",
#         "Find emails about interviews and schedule an interview event with the mentioned participants.",
#         "Summarize my recent emails about team syncs and arrange a meeting accordingly.",
#         "Check emails about budget discussions and schedule a follow-up meeting.",
#         "Fetch emails from Alice about the workshop and create a calendar event for it.",
#         "Get emails mentioning 'demo' and schedule a demo session with the attendees.",
#         "Find emails about client calls and book a meeting with the clients.",
#         "Summarize emails about onboarding and set up an onboarding event.",
#         "Fetch emails about training sessions and schedule the next session on my calendar.",
#         "Find any emails that include event or meeting invitations and add them to my calendar"
#     ]
  
#     thread_id = uuid.uuid4() # Generate a fresh thread ID for this conversation.

#     config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20, "verbose": True}

#     # Configure the invocation with the thread ID.
#     # config = {"configurable": {"thread_id": thread_id}}
#     # The supervisor agent expects a state input
#     # result = supervisor_prebuilt.invoke({"messages": [HumanMessage(content=sample_prompts[10])]}, config=config)
#     result = supervisor_prebuilt.invoke({"messages": [HumanMessage(content=email_event_prompts[3])]}, config=config)

#     print("Agent output:")
#     for message in result["messages"]:
#         message.pretty_print()
