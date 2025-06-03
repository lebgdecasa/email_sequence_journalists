# scheduler.py
"""
Runs every 15 min (or whatever cron you choose) and
  • finds contacts whose `next_action_at` ≤ now
  • determines which template to send based on current state
  • emails the contact via Resend
  • advances the finite-state machine (FSM)
  • schedules the next step
The file is **pure logic**; a tiny wrapper in /api/scheduler.py
will import and execute `run()` so Vercel can hit it.
"""
import os
import pathlib
from datetime import datetime, timedelta, timezone

import pymongo
import resend
from dotenv import load_dotenv

from app import fsm

load_dotenv()
# ── DB connection ────────────────────────────────────────────────
client = pymongo.MongoClient(os.environ["MONGODB_URI"])
resend.api_key = os.environ["RESEND_API_KEY"]


db = client["contacts"]  # database   → contacts
contacts_c = db["contacts"]

# ── Helper: load template once and cache it ──────────────────────
TEMPLATE_DIR = pathlib.Path(__file__).with_suffix("").parent / "templates"
_cache: dict[str, str] = {}


def load_template(code: str) -> str:
    if code not in _cache:
        path = TEMPLATE_DIR / f"{code}.html"
        _cache[code] = path.read_text(encoding="utf-8")
    return _cache[code]


def send_mail(to: str, subject: str, html: str) -> str:
    response = resend.Emails.send(
        {
            "from": os.environ["FROM_EMAIL"],
            "to": [to],
            "subject": subject,
            "html": html,
        }
    )
    return response["id"]


# ── Main loop ────────────────────────────────────────────────────
def run(max_batch: int = 50) -> None:
    now = datetime.now(timezone.utc)

    due_contacts = list(
        contacts_c.find({"next_action_at": {"$lte": now}}).limit(max_batch)
    )

    if not due_contacts:
        print("✅ Scheduler: nothing due")
        return

    for c in due_contacts:
        try:
            next_email_code = fsm.pick_template(c["current_state"])

            # ── build a single dict with ALL placeholders ───────────────
            tags = c.get("merge_tags", {}).copy()
            tags.update(
                {
                    "first_name": c.get("first_name", "there"),
                    "publication": c.get("publication", "your site"),
                }
            )

            html_body = load_template(next_email_code).format(**tags)

            msg_id = send_mail(
                to=c["email"],
                subject=fsm.subject_for(next_email_code, **tags),
                html=html_body,
            )

            new_state, wait_hours = fsm.advance(c["current_state"], "timer")
            contacts_c.update_one(
                {"_id": c["_id"]},
                {
                    "$set": {
                        "current_state": new_state,
                        "next_action_at": now + timedelta(hours=wait_hours),
                    },
                    "$push": {
                        "messages_sent": {
                            "provider_id": msg_id,
                            "template": next_email_code,
                            "ts": now,
                        }
                    },
                },
            )
            print(f"📤 {c['email']} → {next_email_code} ({msg_id})")

        except Exception as exc:  # noqa: BLE001
            print(f"⚠️  failed for {c['email']}: {exc}", flush=True)


if __name__ == "__main__":
    run()
