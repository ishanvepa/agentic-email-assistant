from langchain_core.agents import ToolAgent
from backend.tools.email_fetcher import fetch_emails

inbox_reader_agent = ToolAgent(
    name="inbox_reader_agent",
    description="Fetches recent emails from Gmail",
    func=fetch_emails
)
