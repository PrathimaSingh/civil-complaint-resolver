from langchain_core.messages import AIMessage

from civic_redressal.workflow.state import ComplaintState
from civic_redressal.workflow.util import create_complaint


def run_registration_agent(state: ComplaintState) -> dict:
    authority = state.get("authority") or "Other"
    return create_complaint(state, authority)


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