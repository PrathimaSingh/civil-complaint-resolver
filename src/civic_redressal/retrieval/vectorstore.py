import os
from langchain_chroma import Chroma
from civic_redressal.config import CHROMA_DB_DIR, COLLECTION_NAME
from civic_redressal.retrieval.embeddings import get_embeddings

def get_vectorstore() -> Chroma:
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)
    return Chroma(
        persist_directory=CHROMA_DB_DIR,
        embedding_function=get_embeddings(),
        collection_name=COLLECTION_NAME,
    )