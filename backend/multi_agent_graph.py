from langchain_core.messages import HumanMessage

from langgraph.graph import StateGraph, START, END # Core LangGraph classes and special node names
from utils import show_graph # Utility function to visualize the graph (assumed to be in a utils.py file)
from langgraph.prebuilt import create_react_agent # Import the pre-built ReAct agent creator
# from agents.llm_utils import get_llm_with_fetch_k_emails_tools
from dotenv import load_dotenv # Import function to load environment variables
from langchain_openai import ChatOpenAI # Import the OpenAI chat model
from langgraph.checkpoint.memory import MemorySaver # For short-term memory (thread-level state persistence)
from langgraph.store.memory import InMemoryStore
# from agents import inbox_reader_agent

#tool imports
from email_fetcher import fetch_k_emails
from backend.state import State
from langgraph_supervisor import create_supervisor
import uuid


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
    You are a specialized subagent in a team of assistants, focused on retrieving email information for the user. You are routed only for email-fetching related questions, so respond exclusively to those.

    You have access to the fetch_k_emails tool, which allows you to retrieve the k most recent emails from a user's inbox with custom keyword filtering. Use this tool to help users fetch their most recent emails with keyword querying.

    If you are unable to retrieve the requested email information, politely inform the user and ask if they would like to search for something else.

    CORE RESPONSIBILITIES:
    - Retrieve email content from the user's inbox
    - Provide details such as sender, subject, date, and body of the emails
    - Always maintain a professional, friendly, and helpful tone

    You may receive additional context to help answer the user's query. This context will be provided below:
    """

# Supervisor prompt tailored for email/inbox reading
supervisor_prompt = """
You are a supervisor agent responsible for routing user queries to the appropriate subagent.
Your only available subagent is the inbox_reader_agent, which specializes in retrieving email information for the user.
Always route relevant email-fetching or inbox-related queries to the inbox_reader_agent.
If the query is not related to email fetching, politely inform the user that only email-related queries are supported.
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




# Create the supervisor after subagents are defined
supervisor_prebuilt_workflow = create_supervisor(
    agents=[inbox_reader_agent],      # Only the inbox_reader_agent is available
    output_mode="last_message",       # Output only the last message from the routed agent
    model=llm,                        # The LLM to act as the supervisor
    prompt=supervisor_prompt,         # The system prompt guiding the supervisor's behavior
    state_schema=State                # The shared state schema for the entire multi-agent graph
)

supervisor_prebuilt = supervisor_prebuilt_workflow.compile(name="supervisor_prebuilt", checkpointer=checkpointer, store=in_memory_store)













show_graph(supervisor_prebuilt)

# Test the agent with a sample state and message
if __name__ == "__main__":
    # Example: simulate a user asking for recent emails about meetings
    question = "Show me the past 10 emails relating to interviews."
    thread_id = uuid.uuid4() # Generate a fresh thread ID for this conversation.

    config = {"configurable": {"thread_id": thread_id}}

    # Configure the invocation with the thread ID.
    # config = {"configurable": {"thread_id": thread_id}}
    # The supervisor agent expects a state input
    result = supervisor_prebuilt.invoke({"messages": [HumanMessage(content=question)]}, config=config)
    print("Agent output:")
    for message in result["messages"]:
        message.pretty_print()
