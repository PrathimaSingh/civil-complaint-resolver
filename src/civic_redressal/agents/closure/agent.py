import os
from datetime import datetime
from langchain_core.messages import AIMessage

from civic_redressal.db.json_db import complaints_db, save_complaints_db
from civic_redressal.retrieval.complaint_repository import store_complaint_image
from civic_redressal.workflow.state import ComplaintState


def run_closure_agent(state: ComplaintState) -> dict:
    complaint_id = state.get("complaint_id")
    if not complaint_id or complaint_id not in complaints_db:
        return {"messages": [AIMessage(content="Complaint ID not found.")]}

    resolved_image_path = state.get("resolved_image_path")
    if resolved_image_path and os.path.exists(resolved_image_path):
        complaints_db[complaint_id]["resolved_image_path"] = resolved_image_path

    complaints_db[complaint_id]["status"] = "closed"
    complaints_db[complaint_id]["closedat"] = datetime.now().isoformat()
    save_complaints_db(complaints_db)

    store_complaint_image(
        image_path=complaints_db[complaint_id]["image_path"],
        complaint_id=complaint_id,
        complaint_type=complaints_db[complaint_id]["type"],
        complaint_subtype=complaints_db[complaint_id]["subtype"],
        description="Resolved",
        authority=complaints_db[complaint_id]["authority"],
        status="closed",
        resolved_image_path=resolved_image_path,
    )

    return {
        "status": "closed",
        "messages": [AIMessage(content=f"Complaint {complaint_id} closed successfully.")],
    }