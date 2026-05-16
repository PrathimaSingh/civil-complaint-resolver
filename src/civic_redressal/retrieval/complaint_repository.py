from datetime import datetime
import json
import os
import uuid
from typing import Dict, List, Optional
from langchain_core.documents import Document
import pandas as pd
from civic_redressal.retrieval.vectorstore import get_vectorstore
from civic_redressal.retrieval.documents import build_document_text, build_query

def store_complaint(
    complaint_id: str,
    title: str,
    description: str,
    category: str,
    sub_category: Optional[str],
    civic_agency: str,
    analysis: str,
    severity: Optional[str],
    confidence: Optional[float],
    image_path: Optional[str],
    image_hash: Optional[str] = None,
    image_caption: Optional[str] = None,
    status: str = "open"
) -> str:
    """Store complaint in Vector DB (supports both image and text-only complaints)"""
    vectorstore = get_vectorstore()

    print("In store_complaint")
    print(f"Storing complaint → ID: {complaint_id} | Title: {title} | Category: {category} | Subcategory: {sub_category} | Authority: {civic_agency} | Has Image: {bool(image_path)} | Severity: {severity} | Confidence: {confidence}  | Status: {status}  | Analysis: {analysis}  | Image Caption: {image_caption}  | Image Hash: {image_hash}")
    content = build_document_text({
        "title": title,
        "description": description,
        "image_caption": image_caption or "",
        "category": category,
        "sub_category": sub_category,
        "civic_agency": civic_agency
    })

    metadata = {
        "complaint_id": complaint_id,
        "title": title,
        "description": description,
        "status": status,
        "analysis": analysis,
        "category": category.lower(),
        "sub_category": sub_category,
        "severity": severity or "other",
        "confidence": confidence,
        "civic_agency": civic_agency,
        "image_path": image_path or "",
        "image_hash": image_hash or "",
        "image_caption": image_caption or "",
        "timestamp": datetime.now().isoformat()
    }

    doc_id = f"comp_{complaint_id}_{uuid.uuid4().hex[:6]}"
    doc = Document(
        page_content=content,
        metadata=metadata
    )

    vectorstore.add_documents([doc], ids=[doc_id])
    print(f"Stored in Vector DB → Complaint ID: {complaint_id} | Type: {category} | Subtype: {sub_category} | Authority: {civic_agency} | Has Image: {bool(image_path)}")
    
    return doc_id
def store_multiple_documents_in_vector_db(complaints):
    """
    complaints = [
        {
            "title": "...",
            "description": "...",
            "image_caption": "...",
            "category": "...",
            "sub_category": "...",
            "civic_agency": "...",
            "complaint_id": "optional_id"
        }
    ]
    """

    documents = []
    ids = []

    for item in complaints:
        doc_item = {
            "title": item["title"],
            "description": item["description"],
            "image_caption": item.get("image_caption", ""),
            "category": item["complaint_type"],
            "sub_category": item["complaint_subtype"],
            "civic_agency": item["authority"],
        }
        doc_text = build_document_text(doc_item)
        metadata = {
            "complaint_id": item.get("complaint_id", str(uuid.uuid4())),
            "title": doc_item["title"],
            "description": doc_item["description"],
            "category": doc_item["category"],
            "sub_category": doc_item["sub_category"],
            "civic_agency": doc_item["civic_agency"],
            "analysis": item.get("analysis", ""),
            "severity": item.get("severity", "other"),
            "confidence": item.get("confidence", None),
            "image_path": item.get("image_path", ""),
            "image_hash": item.get("image_hash", ""),
            "image_caption": item.get("image_caption", ""),
            "status": item.get("status", "open"),
            "timestamp": datetime.now().isoformat()
        }

        doc_id = f"comp_{item.get('complaint_id', str(uuid.uuid4()))}_{uuid.uuid4().hex[:6]}"

        print(f"Stored in Vector DB → Complaint ID: {item.get('complaint_id', str(uuid.uuid4()))} \
              | Type: {doc_item['category']} | Subtype: {doc_item['sub_category']} | Authority: {doc_item['civic_agency']} \
                  | Has Image: {bool(item.get('image_path', ''))} | Image Caption: {item.get('image_caption', '')}")

        documents.append(Document(page_content=doc_text, metadata=metadata))
        ids.append(doc_id)

    get_vectorstore().add_documents(documents=documents, ids=ids)

    return ids

def retrieve_top_k_complaints(title="", description="", image_caption="", category="", sub_category="", civic_agency="", top_k=5, metadata_filter=None) -> List[Document]:
    query = build_query(title, description, image_caption, category, sub_category, civic_agency)
    results = get_vectorstore().similarity_search_with_score(
        query=query,
        k=top_k,
        filter=metadata_filter
    )
    output = []
    for doc, score in results:
        output.append({
            "title": doc.metadata.get("title", ""),
            "description": doc.metadata.get("description", ""),
            "image_caption": doc.metadata.get("image_caption", ""),
            "category": doc.metadata.get("category", ""),
            "sub_category": doc.metadata.get("sub_category", ""),
            "civic_agency": doc.metadata.get("civic_agency", ""),
            "score": round(float(score), 4),  # Distance (lower = more similar)
            "content": doc.page_content
        })
    return output

# ====================== LIST COMPLAINTS ======================
def list_all_complaints():
    """Retrieve and display all complaints from Chroma vector DB."""
    
    # Get collection stats first
    collection = get_vectorstore()._collection
    print(f"Fetching all complaints from Vector DB, Collection stats: {collection} ")
    total_count = collection.count()
    if total_count == 0:
        print("Vector DB is empty.")
        return []
    
    print(f"Total complaints in Vector DB: {total_count}")

    # Fetch ALL documents (use large n_results, no fetch_k)
    all_docs = get_vectorstore().similarity_search(
        query="civic complaint",  # Dummy query to fetch everything
        k=10000,  # Fetch exactly the total count
    )
    
    if not all_docs:
        print("No complaints found in the vector DB.")
        return []
    
    complaints = []
    for i, doc in enumerate(all_docs, 1):
        meta = doc.metadata
        complaints.append({
            "id": i,
            "complaint_id": meta.get("complaint_id", "N/A"),
            "title": meta.get("title", "N/A"),
            "description": meta.get("description", "N/A"),
            "category": meta.get("category", "N/A"),
            "sub_category": meta.get("sub_category", "N/A"),
            "civic_agency": meta.get("civic_agency", "N/A"),
            "analysis": meta.get("analysis", "N/A"),
            "severity": meta.get("severity", "N/A"),
            "confidence": meta.get("confidence", "N/A"),
            "status": meta.get("status", "N/A"),
            "created_at": meta.get("timestamp", "N/A"),
            "image_path": meta.get("image_path", ""),
            "image_hash": meta.get("image_hash", ""),
            "image_caption": meta.get("image_caption", "N/A"),
            "page_content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
        })
    
    df = pd.DataFrame(complaints)
    print(f"Found {len(complaints)} complaints in Chroma DB.")
    
    # Save to CSV and JSON
    df.to_csv("results/all_complaints_from_vector_db.csv", index=False)
    with open("results/all_complaints_from_vector_db.json", "w", encoding="utf-8") as f:
        json.dump(complaints, f, ensure_ascii=False, indent=2)
    
    print("\nExported to:")
    print("- results/all_complaints_from_vector_db.csv")
    print("- results/all_complaints_from_vector_db.json")
    
    return complaints
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
    # Only validate file existence for local paths, not URLs
    is_url = has_image and image_path.startswith(('http://', 'https://'))
    if has_image and not is_url and not os.path.exists(image_path):
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
        metadata=metadata,
        embeddings=None  # Let Chroma compute embeddings automatically
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


def get_complaint_by_id(complaint_id: str) -> dict:
    """Retrieve specific complaint from vector DB"""
    vectorstore = get_vectorstore()
    results = vectorstore.get(
        where={"complaint_id": complaint_id}
    )
    return results
