import os

import resend  # uses RESEND_API_KEY env var
from pydantic import BaseModel, EmailStr


class OutboundEmail(BaseModel):
    to: EmailStr
    subject: str
    html: str


_client = resend.Resend(os.environ["RESEND_API_KEY"])


def send(email: OutboundEmail) -> str:
    """Send mail and return Resend message-id."""
    res = _client.emails.send(
        {
            "from": os.getenv("FROM_EMAIL"),
            "to": [email.to],
            "subject": email.subject,
            "html": email.html,
        }
    )
    return res["id"]
