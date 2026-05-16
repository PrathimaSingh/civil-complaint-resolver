from langchain_ollama import OllamaEmbeddings
from civic_redressal.config import EMBEDDING_MODEL

def get_embeddings():
    return OllamaEmbeddings(model=EMBEDDING_MODEL)