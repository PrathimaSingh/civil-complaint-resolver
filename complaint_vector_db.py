# complaint_vector_db.py
# Dedicated Vector Database for Civil Complaints (Images + Metadata)

import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from PIL import Image  # Optional: to validate images

# ========================= CONFIG =========================
CHROMA_DB_DIR = "./chroma_complaints_db"
COLLECTION_NAME = "civil_complaints"

# Use a good text embedding model (nomic-embed-text works well with Ollama)
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Initialize or load Vector Store
def get_vectorstore() -> Chroma:
    """Create or load the Chroma vector database"""
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)
    
    vectorstore = Chroma(
        persist_directory=CHROMA_DB_DIR,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME
    )
    print(f"Vector Database ready → {CHROMA_DB_DIR} | Collection: {COLLECTION_NAME}")
    return vectorstore


# ====================== STORE COMPLAINT IMAGE ======================
def store_complaint_image(
    image_path: str,
    complaint_id: str,
    complaint_type: str,
    complaint_subtype: Optional[str] = None,
    severity: Optional[str] = None,
    confidence: Optional[float] = None,
    description: str = "",
    authority: str = "",
    status: str = "open",
    resolved_image_path: Optional[str] = None,
    additional_metadata: Optional[Dict] = None
) -> str:
    """
    Store complaint in Vector DB (supports both image and text-only complaints)
    """
    # Check if image exists only if image_path is provided and not empty
    has_image = bool(image_path and image_path.strip())
    if has_image and not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    vectorstore = get_vectorstore()

    # Create rich document for RAG
    content = f"""Complaint ID: {complaint_id}
Type: {complaint_type}
Subtype: {complaint_subtype or 'N/A'}
Severity: {severity or 'N/A'}
Confidence: {confidence or 'N/A'}
Authority: {authority}
Description: {description}
Status: {status}
Created: {datetime.now().isoformat()}
Has Image: {has_image}
"""

    metadata = {
        "complaint_id": complaint_id,
        "type": complaint_type.lower(),
        "subtype": (complaint_subtype or "other").lower(),
        "severity": (severity or "other").lower(),
        "confidence": confidence,
        "authority": authority,
        "status": status,
        "image_path": image_path if has_image else "",
        "has_image": has_image,
        "resolved_image_path": resolved_image_path or "",
        "timestamp": datetime.now().isoformat(),
        "source": "civil_complaint",
        **(additional_metadata or {})
    }

    # Unique ID for Chroma
    doc_id = f"comp_{complaint_id}_{uuid.uuid4().hex[:6]}"

    doc = Document(
        page_content=content,
        metadata=metadata
    )

    # Add to vector database
    vectorstore.add_documents([doc], ids=[doc_id])

    complaint_type_display = f"{complaint_type} ({complaint_subtype})" if complaint_subtype else complaint_type
    print(f"Stored in Vector DB → Complaint ID: {complaint_id} | Type: {complaint_type_display} | Status: {status} | Has Image: {has_image}")

    # Also store resolved image if provided (as separate document)
    if resolved_image_path and os.path.exists(resolved_image_path):
        resolved_doc = Document(
            page_content=f"RESOLVED Complaint ID: {complaint_id}\nStatus: closed\nDescription: {description}",
            metadata={
                "complaint_id": complaint_id,
                "type": complaint_type.lower(),
                "subtype": (complaint_subtype or "other").lower(),
                "severity": (severity or "other").lower(),
                "confidence": confidence,
                "status": "closed",
                "resolved_image_path": resolved_image_path,
                "timestamp": datetime.now().isoformat()
            }
        )
        resolved_id = f"resolved_{complaint_id}"
        vectorstore.add_documents([resolved_doc], ids=[resolved_id])
        print(f"Stored Resolved Image in Vector DB → {complaint_id}")

    return doc_id


# ====================== SEARCH / RAG HELPER ======================
def search_complaints(query: str, k: int = 5) -> List[Document]:
    """Search past complaints using RAG (used by tracker & router)"""
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": 20, "lambda_mult": 0.7}
    )
    return retriever.invoke(query)


def get_complaint_by_id(complaint_id: str) -> List[Document]:
    """Retrieve specific complaint from vector DB"""
    vectorstore = get_vectorstore()
    results = vectorstore.get(
        where={"complaint_id": complaint_id}
    )
    return results


# ====================== UTILITY ======================
def list_all_complaints(limit: int = 50):
    """For debugging / analytics"""
    vectorstore = get_vectorstore()
    results = vectorstore.get(limit=limit)
    print(f"Total documents in Vector DB: {len(results.get('ids', []))}")
    return results


# Test / Initialization
if __name__ == "__main__":
    print("=== Civil Complaint Vector Database ===")
    vs = get_vectorstore()
    list_all_complaints()