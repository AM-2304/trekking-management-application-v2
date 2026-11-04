"""Sending mail with the standard library only.

MAIL_BACKEND picks the backend: "file" writes HTML into instance/outbox/ (no mail
server needed), "smtp" sends for real.
"""

import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage

from flask import current_app


def _safe_filename(text):
    """Make a string safe to use as a filename."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text)[:60]


def send_mail(to, subject, html):
    """Send one message. Returns the file path, or None for SMTP."""
    backend = current_app.config.get("MAIL_BACKEND", "file")

    if backend == "smtp":
        message = EmailMessage()
        message["From"] = current_app.config["MAIL_SENDER"]
        message["To"] = to
        message["Subject"] = subject
        message.set_content("This message requires an HTML-capable mail reader.")
        message.add_alternative(html, subtype="html")

        with smtplib.SMTP(
            current_app.config["MAIL_SERVER"], current_app.config["MAIL_PORT"]
        ) as server:
            server.send_message(message)
        return None

    outbox = current_app.config["OUTBOX_DIR"]
    os.makedirs(outbox, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{stamp}_{_safe_filename(to)}_{_safe_filename(subject)}.html"
    path = os.path.join(outbox, filename)

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            f"<!doctype html><meta charset='utf-8'>"
            f"<title>{subject}</title>"
            f"<div style=\"font-family:system-ui,sans-serif;max-width:640px;"
            f"margin:2rem auto;padding:1.5rem;border:1px solid #ddd;border-radius:8px\">"
            f"<p style='color:#666;font-size:13px;margin-top:0'>"
            f"<b>To:</b> {to}<br><b>Subject:</b> {subject}</p><hr>{html}</div>"
        )
    return path
