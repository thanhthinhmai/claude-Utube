"""Email: an outbox in SQLite, sent over SMTP or written to files (specs/007 research R8).

Settings come from the environment: SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASS, MAIL_FROM,
STUDIO_URL (links in the mail). With MAIL_DIR set, mails are written there as .eml files instead (tests, local runs)."""
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from . import db, store

MAX_TRIES = 5

TEMPLATES = {
    "verify": ("Confirm your email for Film Studio",
               "Welcome to Film Studio.\n\nConfirm your email to start making films:\n{url}/#/verify/{token}\n\n"
               "The link works once and expires in 24 hours. If you did not sign up, ignore this mail."),
    "reset": ("Reset your Film Studio password",
              "Someone asked to reset the password of this account.\n\nChoose a new password:\n{url}/#/reset/{token}\n\n"
              "The link works once and expires in 1 hour. If it was not you, ignore this mail."),
    "job_done": ("Your job is ready: {name}", "“{name}” is done.\n\nOpen it: {url}/#/jobs/{job}"),
    "job_failed": ("Your job could not finish: {name}",
                   "“{name}” stopped with an error: {error}\n\n{refund}\n\nDetails: {url}/#/jobs/{job}"),
    "review_needed": ("Film Studio needs your answer: {name}",
                      "“{name}” is waiting for you.\n\nOpen it: {url}/#/jobs/{job}"),
    "review_timeout": ("Your job was stopped: {name}",
                       "“{name}” waited {days} days for your answer and was stopped.\n\n{url}/#/jobs/{job}"),
    "account_deleted": ("Your Film Studio account is being deleted",
                        "Your account and all its films and styles will be deleted within 30 days.\n"
                        "If you did not ask for this, reply to this mail right away."),
}


def queue(to: str, template: str, data: dict = None) -> None:
    assert template in TEMPLATES
    with db.tx() as con:
        con.execute('INSERT INTO outbox ("to", template, data, created_at) VALUES (?, ?, ?, ?)',
                    (to, template, json.dumps(data or {}), store.now_iso()))


def render(template: str, data: dict) -> EmailMessage:
    subject, body = TEMPLATES[template]
    values = {"url": os.environ.get("STUDIO_URL", "http://localhost:8787").rstrip("/"), **data}
    m = EmailMessage()
    m["Subject"] = subject.format(**values)
    m["From"] = os.environ.get("MAIL_FROM", "Film Studio <noreply@localhost>")
    m.set_content(body.format(**values))
    return m


def _send(m: EmailMessage) -> None:
    out = os.environ.get("MAIL_DIR")
    if out:
        d = Path(out)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{store.clock():.6f}-{m['To']}.eml").write_bytes(bytes(m))
        return
    host = os.environ.get("SMTP_HOST")
    if not host:
        raise RuntimeError("SMTP_HOST is not set")
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=30) as s:
        s.starttls(context=ssl.create_default_context())
        if os.environ.get("SMTP_USER"):
            s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASS", ""))
        s.send_message(m)


def flush() -> int:
    """Send what is waiting (retries failed mails up to MAX_TRIES). Returns how many were sent.
    Each mail is claimed first, so two processes flushing at once never send it twice."""
    import secrets
    with db.read() as con:
        rows = con.execute('SELECT id, "to", template, data FROM outbox WHERE sent_at IS NULL AND tries < ?',
                           (MAX_TRIES,)).fetchall()
    sent, mark = 0, f"sending:{secrets.token_hex(6)}"
    for r in rows:
        with db.tx() as con:
            if con.execute("UPDATE outbox SET sent_at = ? WHERE id = ? AND sent_at IS NULL", (mark, r["id"])).rowcount == 0:
                continue                      # someone else took it
        m = render(r["template"], json.loads(r["data"]))
        m["To"] = r["to"]
        try:
            _send(m)
        except Exception as e:     # noqa: BLE001 - any delivery problem is retried later
            with db.tx() as con:
                con.execute("UPDATE outbox SET sent_at = NULL, tries = tries + 1, last_error = ? WHERE id = ?",
                            (str(e)[:300], r["id"]))
            continue
        with db.tx() as con:
            con.execute("UPDATE outbox SET sent_at = ?, tries = tries + 1 WHERE id = ?", (store.now_iso(), r["id"]))
        sent += 1
    return sent
