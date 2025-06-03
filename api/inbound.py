import os

import pymongo
from dotenv import load_dotenv

from app import fsm

load_dotenv()
client = pymongo.MongoClient(os.environ["MONGODB_URI"])
db = client.get_default_database()


def handler(request):
    payload = request.json()
    db.messages.insert_one(payload)
    fsm.handle_inbound(payload)  # decide new state
    return {"status": "ok"}
