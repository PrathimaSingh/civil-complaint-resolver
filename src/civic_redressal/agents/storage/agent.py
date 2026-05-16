from langchain_core.messages import AIMessage

from civic_redressal.retrieval.complaint_repository import store_complaint, store_multiple_documents_in_vector_db
from civic_redressal.workflow.state import ComplaintBatchState, ComplaintState


def run_storage_agent(state: ComplaintState) -> dict:
    if not state.get("complaint_id"):
        return {"messages": [AIMessage(content="Skipped storage due to duplicate complaint.")]}

    try:
        docid = store_complaint(
            complaint_id=state.get("complaint_id"),
            title=state.get("title"),
            description=state.get("description"),
            category=state.get("complaint_type"),
            sub_category=state.get("complaint_subtype"),
            analysis=state.get("analysis"),
            civic_agency=state.get("authority"),
            status=state.get("status", "open"),
            severity=state.get("severity"),
            confidence=state.get("confidence"),
            image_path=state.get("image_path"),
            image_hash=state.get("image_hash"),
            image_caption=state.get("image_caption"),
        )
        return {"messages": [AIMessage(content=f"Stored in Vector DB: {docid}")]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Vector DB storage failed: {str(e)}")]}

def run_storage_bulk_agent(state: ComplaintBatchState) -> dict:
    print(f"Storing batch of {len(state.get('complaints', []))} complaints in vector DB...")
    store_multiple_documents_in_vector_db(state.get("complaints", []))
    print("Bulk storage complete.")
    return {"messages": [AIMessage(content="Bulk storage complete.")]}