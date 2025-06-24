from dataclasses import dataclass
from typing import Optional

@dataclass
class Email:
    """
    Data structure for holding email information for agent state sharing.
    """
    subject: str
    sender: str
    body: Optional[str] = None
    date: Optional[str] = None
    id: Optional[str] = None
