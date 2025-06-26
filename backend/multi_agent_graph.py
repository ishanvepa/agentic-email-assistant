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


# Load environment variables from the .env file. The `override=True` argument   
# ensures that variables from the .env file will overwrite existing environment variables.
load_dotenv(override=True)

# Initialize the ChatOpenAI model. We're using a specific model from Llama 3.3 series.
# This `model` object will be used throughout the notebook for all LLM interactions.
llm = ChatOpenAI(model_name="meta-llama/Llama-3.3-70B-Instruct", temperature=0)


# Initializing `InMemoryStore` for long-term memory.
# This store will hold user-specific data like music preferences across sessions.
in_memory_store = InMemoryStore()

# Initializing `MemorySaver` for short-term (thread-level) memory. 
# This checkpointer saves the graph's state after each step, allowing for restarts or interruptions within a thread.
checkpointer = MemorySaver()

# bind tools
# llm = llm.bind_tools([fetch_k_emails])

inbox_reader_agent_prompt = """
You are a specialized subagent focused on retrieving email information for users.

CORE RESPONSIBILITIES:
- Retrieve email content from the user's inbox using the fetch_k_emails tool
- Provide details such as sender, subject, date, and body of the emails
- Always maintain a professional, friendly, and helpful tone

IMPORTANT RULES:
1. ONLY handle requests to fetch or list emails, NOT to summarize or extract key points (summarization is handled by the email_summarizer_agent)
2. When asked for emails, extract the number of emails (k) and any keywords from the request
3. If no number is specified, default to 5 emails
4. If no keywords are given, fetch the most recent emails
5. ONLY call fetch_k_emails ONCE per user request
6. After calling the tool and receiving results, DO NOT call the tool again
7. If you cannot retrieve emails, inform the user politely

RESPONSE FORMAT:
After using the fetch_k_emails tool, present the results clearly with:
- A brief introduction (e.g., "Here are the emails I found:")
- For each email, display the sender, subject, date, and a short snippet or the body
- Separate each email with a line or bullet for clarity

Always respond with the email information once retrieved. Do not ask follow-up questions unless there's an error. If the user asks for a summary or key points, do not handle it and let the email_summarizer_agent respond.
"""
# query = ['meeting', 'zoom', 'schedule', 'calendar', 'invite', 'appointment', 'availability', 'time to meet', 'set up a meeting', 'meeting request', 'meeting inquiry']

email_summarizer_agent_prompt = """
You are a specialized subagent focused on summarizing email content for users.

CORE RESPONSIBILITIES:
- Take email data and create concise, actionable summaries
- Extract key information from multiple emails into digestible bullet points
- Maintain clarity and relevance in all summaries
- Always maintain a professional, helpful tone

IMPORTANT RULES:
1. When asked to summarize emails, extract the number of bullet points requested (max_bullets)
2. If no number is specified, default to 5 bullet points
3. ONLY call summarize_emails ONCE per user request
4. After calling the tool and receiving results, provide the summary and DO NOT call the tool again
5. If you cannot summarize the emails, inform the user politely and explain why
6. Focus on the most important and actionable information from the emails

EXPECTED INPUT:
- You will receive requests like "summarize these emails", "give me bullet points of my emails", "what are the key points from my inbox"
- The user may specify a number of bullet points they want (e.g., "give me 3 key points")

RESPONSE FORMAT:
After using the summarize_emails tool, present the results clearly with:
- A brief introduction (e.g., "Here's a summary of your emails:")
- The bullet points returned by the tool
- Any relevant context about what was summarized

Always respond with the email summary once generated. Do not ask follow-up questions unless there's an error or missing information.
"""


# Supervisor prompt tailored for email/inbox reading
supervisor_prompt = """
You are a supervisor agent responsible for managing multiple AI agents. routing user queries to the appropriate subagent.
Your only available subagents are the inbox_reader_agent, which specializes in retrieving email information for the user, and the email_summarizer_agent, which focuses on summarizing email content.
Any query related to email, inbox, messages, or similar topics should be routed to the inbox_reader_agent.
If the query is not related to email fetching, politely inform the user that only email-related queries are supported.
if the user asks for summarizing emails, route the query to the email_summarizer_agent once emails have been fetched.
email_summarizer_agent should only ever be called after the inbox_reader_agent has fetched the emails.
"""





# def music_assistant(state: State, config: RunnableConfig): 

#     # Fetch long-term memory (user preferences) from the state.
#     # If `loaded_memory` is not present in the state, default to "None".
#     memory = "None" 
#     if "loaded_memory" in state: 
#         memory = state["loaded_memory"]

#     # Generate the system prompt for the music assistant, injecting the loaded memory.
#     music_assistant_prompt = generate_music_assistant_prompt(memory)

#     # Invoke the LLM (`llm_with_music_tools`) with the system prompt and the current message history.
#     # The LLM will decide whether to call a tool or generate a final response.
#     response = llm_with_music_tools.invoke([SystemMessage(music_assistant_prompt)] + state["messages"])
    
#     # Update the state by appending the LLM's response to the `messages` list.
#     # The `add_messages` annotation in `State` ensures this is appended correctly.
#     return {"messages": [response]}

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


# Create the supervisor after subagents are defined
supervisor_prebuilt_workflow = create_supervisor(
    agents=[inbox_reader_agent, summarizer_agent],      # Both agents are available
    output_mode="last_message",       # Output only the last message from the routed agent
    model=llm,                        # The LLM to act as the supervisor
    prompt=supervisor_prompt,         # The system prompt guiding the supervisor's behavior
    state_schema=State                # The shared state schema for the entire multi-agent graph
)

supervisor_prebuilt = supervisor_prebuilt_workflow.compile(name="supervisor_prebuilt", checkpointer=checkpointer, store=in_memory_store)


# Test the agent with a sample state and message
if __name__ == "__main__":
    # Example: simulate a user asking for recent emails about meetings
    show_graph(supervisor_prebuilt)

    sample_prompts = [
        "Please get me 5 emails about meetings and summarize them in 5 bullet points.",
        "Show me the most recent 2 emails from my inbox and summarize them.",
        "Summarize my unread emails in 4 bullet points.",
        "Get the last 3 emails about project updates.",
        "Give me a summary of my emails mentioning 'invoice'.",
        "Fetch my most recent email.",
        "Summarize my inbox.",
        "Fetch me my emails from computer science and summarize them in 3 bullet points.",
        "What are the key points from my last 5 emails?",
        "List my recent emails about deadlines."
    ]    

    thread_id = uuid.uuid4() # Generate a fresh thread ID for this conversation.

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 10}

    # Configure the invocation with the thread ID.
    # config = {"configurable": {"thread_id": thread_id}}
    # The supervisor agent expects a state input
    result = supervisor_prebuilt.invoke({"messages": [HumanMessage(content=sample_prompts[0])]}, config=config)
    print("Agent output:")
    for message in result["messages"]:
        message.pretty_print()
