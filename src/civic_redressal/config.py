import os

INCOMING_FOLDER = "./incoming_complaints"
RESOLVED_FOLDER = "./resolved_complaints"
SENT_MESSAGES_FOLDER = "./sent_messages"
PROMPT_FOLDER = "./prompts"
PROMPT_NUMBER = 1
COMPLAINTS_DB_FILE = "complaints_db.json"

# Create folders
os.makedirs(INCOMING_FOLDER, exist_ok=True)
os.makedirs(RESOLVED_FOLDER, exist_ok=True)
os.makedirs(SENT_MESSAGES_FOLDER, exist_ok=True)
os.makedirs(PROMPT_FOLDER, exist_ok=True)

# Vector DB config
CHROMA_DB_DIR = "./chroma_complaints_db"
COLLECTION_NAME = "civil_complaints"
EMBEDDING_MODEL = "nomic-embed-text"