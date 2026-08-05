"""Thin wrapper around the Resend HTTP API. Uses urllib instead of adding a
new HTTP client dependency -- this is the only outbound email call in the
app, so a whole SDK isn't warranted."""
import json
import urllib.error
import urllib.request

from app.config import settings

RESEND_API_URL = "https://api.resend.com/emails"


class EmailError(Exception):
    pass


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    if not settings.resend_api_key:
        raise EmailError("RESEND_API_KEY is not configured")

    payload = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": "Reset your Finance Engine password",
        "html": (
            f"<p>Someone requested a password reset for this email address.</p>"
            f'<p><a href="{reset_url}">Click here to choose a new password</a>. '
            f"This link expires in {settings.password_reset_expire_minutes} minutes.</p>"
            f"<p>If you didn't request this, you can ignore this email.</p>"
        ),
    }
    request = urllib.request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
    except urllib.error.URLError as exc:
        raise EmailError(f"Failed to send password reset email: {exc}") from exc
