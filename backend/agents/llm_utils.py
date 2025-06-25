from dotenv import load_dotenv # Import function to load environment variables
from langchain_openai import ChatOpenAI # Import the OpenAI chat model
from langgraph.checkpoint.memory import MemorySaver # For short-term memory (thread-level state persistence)
from langgraph.store.memory import InMemoryStore
from agents import inbox_reader_agent
from backend.tools.email_fetcher import fetch_k_emails


# Load environment variables from the .env file. The `override=True` argument
# ensures that variables from the .env file will overwrite existing environment variables.
load_dotenv(dotenv_path=".env", override=True)

# Initialize the ChatOpenAI model. We're using a specific model from Llama 3.3 series.
# This `model` object will be used throughout the notebook for all LLM interactions.
llm = ChatOpenAI(model_name="meta-llama/Llama-3.3-70B-Instruct", temperature=0)


def get_llm_with_fetch_k_emails_tools():
    fetch_k_emails_tools = [fetch_k_emails]
    return llm.bind_tools(fetch_k_emails_tools)


# Initializing `InMemoryStore` for long-term memory. 
# This store will hold user-specific data like music preferences across sessions.
in_memory_store = InMemoryStore()

# Initializing `MemorySaver` for short-term (thread-level) memory. 
# This checkpointer saves the graph's state after each step, allowing for restarts or interruptions within a thread.
checkpointer = MemorySaver()

