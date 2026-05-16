from langchain_core.messages import AIMessage
from datetime import datetime

from civic_redressal.workflow.state import ComplaintState
from civic_redressal.db.json_db import complaints_db, save_complaints_db
from civic_redressal.config import SENT_MESSAGES_FOLDER

def create_complaint(state: ComplaintState, authority: str):
    """Common function to create complaint for any department"""
    if not state.get("complaint_id"):
        return {"messages": [AIMessage(content="Registration skipped due to duplicate")]}

    complaint_id = state["complaint_id"]

    message_text = f"""NEW CIVIL COMPLAINT
Complaint ID     : {complaint_id}
Complaint Title  : {state.get('title', 'N/A')}
Complaint Desc   : {state.get('description', 'N/A')}
Category         : {state.get('complaint_type', 'N/A')}
Analysis         : {state.get('analysis', 'N/A')}
Civic Agency     : {authority}
Submitted Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Image Location   : {state['image_path']}
Image Caption    : {state.get('image_caption', 'N/A')}

Please take necessary action at the earliest.
"""

    msg_path = f"{SENT_MESSAGES_FOLDER}/{complaint_id}.txt"
    with open(msg_path, "w", encoding="utf-8") as f:
        f.write(message_text)

    complaints_db[complaint_id] = {
        "title": state.get("title"),
        "description": state.get("description"),
        "type": state.get("complaint_type"),
        "subtype": state.get("complaint_subtype"),
        "analysis": state.get("analysis"),
        "severity": state.get("severity"),
        "confidence": state.get("confidence"),
        "authority": authority,
        "status": "open",
        "image_path": state["image_path"],
        "image_hash": state.get("image_hash"),
        "image_caption": state.get("image_caption"),
        "resolved_image_path": None,
        "created_at": datetime.now().isoformat(),
        "closed_at": None,
        "message_path": msg_path
    }
    save_complaints_db(complaints_db)

    print(f"✅ Complaint {complaint_id} successfully registered and sent to {authority}")
    return {
        "complaint_message": message_text,
        "status": "open",
        "messages": [AIMessage(content=f"Complaint {complaint_id} created for {authority}")]
    }