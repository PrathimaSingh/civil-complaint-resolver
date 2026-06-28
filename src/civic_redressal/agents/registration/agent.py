import uuid

from langchain_core.messages import AIMessage

from civic_redressal.workflow.state import ComplaintBatchState, ComplaintState
from civic_redressal.workflow.util import create_complaint


def run_registration_agent(state: ComplaintState) -> dict:
    authority = state.get("authority") or "Other"
    if state.get("complaint_type") == "duplicate":
        return {
            **state,
            "complaint_id": None,
            "analysis": "Duplicate complaint - no registration required",
            "complaint_type": "duplicate",
            "messages": [AIMessage(content="Duplicate complaint - no registration required.")],
        }
    if not state.get("complaint_id"):
        complaint_id = f"COMP{str(uuid.uuid4())[:8].upper()}"
        state["complaint_id"] = complaint_id
    registered_complaint = create_complaint(state, authority)
    registered_complaint = {**state, **registered_complaint}
    print(f"Running registration: {registered_complaint}")
    return registered_complaint

def run_registration_bulk_agent(state: ComplaintBatchState) -> dict:
    complaints = state.get("complaints", [])
    registered_complaints = []
    for complaint in complaints:
        registered_complaint = run_registration_agent(complaint)
        registered_complaints.append(registered_complaint)
    return {"complaints": registered_complaints}


def route_to_creator(state: ComplaintState) -> str:
    if state.get("complaint_type") == "duplicate":
        return "storage"

    auth = state.get("authority")
    if auth == "BBMP":
        return "creatorbbmp"
    elif auth == "BWSSB":
        return "creatorbwssb"
    elif auth == "BESCOM":
        return "creatorbescom"
    elif auth == "BDA":
        return "creatorbda"
    elif auth == "BCP":
        return "creatorbcp"
    elif auth == "BTP":
        return "creatorbtp"
    elif auth == "KSPCB":
        return "creatorkspcb"
    return "creatorother"