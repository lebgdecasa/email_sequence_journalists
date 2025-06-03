import datetime
import os
import uuid

import pymongo
from dotenv import load_dotenv

load_dotenv()

client = pymongo.MongoClient(os.environ["MONGODB_URI"])

db = client["contacts"]  # database   → contacts
contacts_c = db["contacts"]  # start clean

contact = {
    "_id": uuid.uuid4().hex,
    "email": "alice@example.com",
    "first_name": "Alice",
    "publication": "TechCrunch",
    "current_state": "NEW",
    "next_action_at": datetime.datetime.utcnow(),  # due now
    "merge_tags": {
        "article_topic": "AI-driven email",
        "article_summary": "Start-ups race to automate outreach.",
        "key_stat": "Open-rates up 32 %",
        "sender_name": "Jad",
    },
}
db.contacts.insert_one(contact)
print("✔️  Inserted dummy contact")
