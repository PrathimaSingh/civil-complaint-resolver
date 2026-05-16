from langchain_core.messages import AIMessage

from civic_redressal.workflow.state import ComplaintState
from civic_redressal.utils.constants import CATEGORY_CIVIC_AGENCY_MAP


def run_routing_agent(state: ComplaintState) -> dict:
    if state.get("complaint_type") == "duplicate":
        return {
            "authority": None,
            "messages": [AIMessage(content="Duplicate complaint - no routing required.")],
        }

    ctype = str(state.get("complaint_type", "")).strip()

    if ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BBMP", []):
        actualauthority = "BBMP"
    elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BESCOM", []):
        actualauthority = "BESCOM"
    elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BWSSB", []):
        actualauthority = "BWSSB"
    elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BCP", []):
        actualauthority = "BCP"
    elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BTP", []):
        actualauthority = "BTP"
    elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("KSPCB", []):
        actualauthority = "KSPCB"
    elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BDA", []):
        actualauthority = "BDA"
    else:
        actualauthority = "Other"

    return {
        "authority": actualauthority,
        "messages": [AIMessage(content=f"Routed to {actualauthority} for category {ctype}")],
    }