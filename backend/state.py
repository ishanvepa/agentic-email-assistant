from typing_extensions import TypedDict # For defining dictionaries with type hints
from typing import Annotated, List, Optional, Dict, Any # For type hinting lists, optionals, and adding annotations
from langgraph.graph.message import AnyMessage, add_messages # type: ignore # For managing messages in the graph state
from langgraph.managed.is_last_step import RemainingSteps # For tracking recursion limits

class State(TypedDict):
    """Represents the state of our LangGraph agent."""
    # user_id: Stores the unique identifier for the current user.
    user_id: str
    
    # messages: A list of messages that form the conversation history.
    # Annotated with `add_messages` to ensure new messages are appended rather than overwritten.
    messages: Annotated[list[AnyMessage], add_messages]
    
    # loaded_memory: Stores information loaded from the long-term memory store, 
    # typically user preferences or historical context.
    loaded_memory: str
    
    # remaining_steps: Used by LangGraph to track the number of allowed steps 
    # to prevent infinite loops in cyclic graphs.
    remaining_steps: RemainingSteps 

    # emails: Optional[List[Dict[str, Any]]] 
