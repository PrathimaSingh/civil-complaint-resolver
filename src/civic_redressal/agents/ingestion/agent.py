from langchain_core.messages import AIMessage

from civic_redressal.workflow.state import ComplaintBatchState, ComplaintState
from civil_complaint_resolver import find_duplicate_image

def run_ingestion_agent(state: ComplaintState) -> dict:
    # For now, this agent just passes through the data. In future, it can be used for data validation, enrichment, etc.
    image_path = state.get("image_path")
    has_imageinput = bool(image_path and image_path.strip())
    print(f"Running ingestion agent for complaint with title: '{state.get('title', 'N/A')}' | Complaint Type: {state.get('complaint_type', 'N/A')} | Complaint Subtype: {state.get('complaint_subtype', 'N/A')} | Authority: {state.get('authority', 'N/A')} | Has Image: {has_imageinput}")

    if has_imageinput:
        duplicate = find_duplicate_image(image_path)
        if duplicate:
            return {
                "complaint_id": None,
                "analysis": "Duplicate image detected",
                "complaint_type": "duplicate",
                "messages": [AIMessage(content=f"Duplicate image found ID {duplicate['complaint_id']}. Skipped.")],
            }

    return {
        "title": state.get("title"),
        "description": state.get("description"),
        "image_path": state.get("image_path"),
        "complaint_type": state.get("complaint_type", "other"),
        "complaint_subtype": state.get("complaint_subtype", "other"),
        "authority": state.get("authority", "other"),
        "messages": [AIMessage(content="Ingestion complete.")],
    }

def run_ingestion_bulk_agent(state: ComplaintBatchState) -> dict:
    print(f"Running ingestion for batch of {len(state.get('complaints', []))} complaints...")
    processed_complaints = []
    for complaint in state.get("complaints", []):
        result = run_ingestion_agent(complaint)
        print(f"Ingestion result for complaint '{complaint.get('title', 'N/A')}': {result.get('description', 'N/A')} | Type: {result.get('complaint_type', 'N/A')} \
              | Subtype: {result.get('complaint_subtype', 'N/A')} | Authority: {result.get('authority', 'N/A')}")
        processed_complaints.append(result)
    return {
        "complaints": processed_complaints
    }