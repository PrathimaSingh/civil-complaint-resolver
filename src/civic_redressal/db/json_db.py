
import os
import json
from civic_redressal.config import COMPLAINTS_DB_FILE

def load_complaints_db() -> dict:
    if os.path.exists(COMPLAINTS_DB_FILE):
        with open(COMPLAINTS_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_complaints_db(db: dict):
    with open(COMPLAINTS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

complaints_db = load_complaints_db()