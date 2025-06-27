import os
from openai import OpenAI
from dotenv import load_dotenv
from langchain_core.tools import tool 

load_dotenv()

client = OpenAI(
    # This is the default and can be omitted
    api_key = os.environ.get("OPENAI_API_KEY"),
    base_url= os.environ.get("OPENAI_API_BASE")
)

@tool
def summarize_emails(emails: (list[dict[str, str]]), max_bullets: int = 5) -> str:
    """
    Summarizes a list of emails into concise bullet points.
    This tool is only to be called by the email_summarizer_agent.

    Args:
        emails (list[dict[str, str]]): A list of email dictionaries, each containing keys such as 'subject', 'sender', 'date', 'body', and 'id'.
        max_bullets (int, optional): The maximum number of bullet points to return based on what the user wants. If none specified, then defaults to 5.
    Returns:
        str: A string of summarized bullet points, each representing key point(s) from the emails.
    """
    print("Summarizing emails...")
    print(str(emails))
    combined_text = "\n\n".join(
        f"Subject: {email.get('subject', '')}\nSender: {email.get('sender', '')}\nDate: {email.get('date', '')}\nBody: {email.get('body', '')}"
        for email in emails
    )
    print("Combined text for summarization:" + str(combined_text))
    prompt = (
        "Summarize the following emails into concise bullet points:\n\n"
        f"{combined_text}\n\nBullet points:"
    )

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "You summarize emails into bullet points."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    summary_text = response.choices[0].message.content or ""
    print("Summary text:" + str(summary_text))
    # bullets = [line.strip('- ').strip() for line in summary_text.split('\n') if line.strip().startswith('-')]
    # return [f"- {b}" for b in bullets][:max_bullets]
    return summary_text

# Example usage:
# if __name__ == "__main__":
#     emails = [
#         {
#             'subject': "Project Kickoff Meeting",
#             'sender': "alice@example.com",
#             'body': "We will have the project kickoff meeting on Tuesday at 2pm. Please prepare your initial ideas.",
#             'date': "2024-06-10",
#             'id': "msg001"
#         },
#         {
#             'subject': "Weekly Report Submission",
#             'sender': "bob@example.com",
#             'body': "Reminder to submit your weekly reports by end of day Friday.",
#             'date': "2024-06-09",
#             'id': "msg002"
#         },
#         {
#             'subject': "Client Feedback",
#             'sender': "carol@example.com",
#             'body': "The client has provided feedback on the latest deliverable. Please review the attached document.",
#             'date': "2024-06-08",
#             'id': "msg003"
#         },
#         {
#             'subject': "Team Lunch",
#             'sender': "dave@example.com",
#             'body': "Let's have a team lunch this Thursday at noon. RSVP if you can make it.",
#             'date': "2024-06-07",
#             'id': "msg004"
#         },
#         {
#             'subject': "System Maintenance",
#             'sender': "it-support@example.com",
#             'body': "Scheduled system maintenance will occur this Saturday from 1am to 5am. Services may be unavailable.",
#             'date': "2024-06-06",
#             'id': "msg005"
#         }
#     ]
#     bullets = summarize_emails(emails)
#     for bullet in bullets:
#         print(bullet)
