import uuid
from langchain_core.messages import AIMessage

from civic_redressal.agents.llm.agent import run_text_json_agent, run_vision_json_agent
from civic_redressal.agents.retrieval.prompt import RETRIEVAL_RAG_PROMPT, RETRIEVAL_VISION_RAG_PROMPT
from civic_redressal.retrieval.complaint_repository import retrieve_top_k_complaints
from civic_redressal.workflow.state import ComplaintState
from civic_redressal.utils.constants import (
    CATEGORY_PROMPT_OPTIONS,
    SUBCATEGORY_PROMPT_OPTIONS,
    CIVIC_AGENCY_PROMPT_OPTIONS,
)
from civic_redressal.utils.util import format_context, image_to_base64, image_to_base64, read_prompt, sanitize_text


def run_retrieval_agent(state: ComplaintState, topk: int = 5, metadatafilter=None) -> dict:
    retrieved = retrieve_top_k_complaints(
        title=state.get("title") or "",
        description=state.get("description") or "",
        image_caption=state.get("image_caption") or "",
        top_k=topk,
        metadata_filter=metadatafilter,
    )
    context = format_context(retrieved)
    return {
        "similar_complaints": context,
        "messages": [AIMessage(content=f"Retrieved {len(retrieved)} similar complaints for reference.")],
    }

def run_retrieval_llm_agent(state: ComplaintState) -> dict:
    similar_complaints = state.get("similar_complaints") or ""
    title = sanitize_text(state.get("title"))
    description = sanitize_text(state.get("description"))

    prompt = RETRIEVAL_RAG_PROMPT
    prompt = prompt.replace("{CATEGORY_PROMPT_OPTIONS}", CATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace("{SUBCATEGORY_PROMPT_OPTIONS}", SUBCATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace("{CIVIC_AGENCY_PROMPT_OPTIONS}", CIVIC_AGENCY_PROMPT_OPTIONS)
    prompt = prompt.replace("{similar_complaints}", similar_complaints)
    prompt = prompt.replace("{title}", title)
    prompt = prompt.replace("{description}", description)
    try:
        result = run_text_json_agent(prompt, model="llama3.2:3b")
        complaint_id = f"COMP{str(uuid.uuid4())[:8].upper()}"

        return {
            "complaint_id": complaint_id,
            "analysis": result.get("description", "Unknown issue"),
            "complaint_type": result.get("category", "other"),
            "complaint_subtype": result.get("sub_category", "other"),
            "authority": result.get("civic_agency", "other"),
            "severity": result.get("severity", "NA"),
            "confidence": result.get("confidence", 50),
            "title": title,
            "description": description,
            "messages": [AIMessage(content="RAG analysis complete.")],
        }
    except Exception:
        return {
            "messages": [AIMessage(content="RAG analysis failed, proceeding without it.")],
        }

def run_retrieval_vision_llm_agent(state: ComplaintState) -> dict:
    similar_complaints = state.get("similar_complaints") or ""
    title = sanitize_text(state.get("title"))
    description = sanitize_text(state.get("description"))
    image_path = state.get("image_path")
    base64_image = image_to_base64(image_path)

    prompt = RETRIEVAL_VISION_RAG_PROMPT
    prompt = prompt.replace("{CATEGORY_PROMPT_OPTIONS}", CATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace("{SUBCATEGORY_PROMPT_OPTIONS}", SUBCATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace("{CIVIC_AGENCY_PROMPT_OPTIONS}", CIVIC_AGENCY_PROMPT_OPTIONS)
    prompt = prompt.replace("{similar_complaints}", similar_complaints)
    prompt = prompt.replace("{title}", title)
    prompt = prompt.replace("{description}", description)
    try:
        result = run_vision_json_agent(prompt, base64_image, model="gemma4:e4b")
        complaint_id = f"COMP{str(uuid.uuid4())[:8].upper()}"

        return {
            "complaint_id": complaint_id,
            "analysis": result.get("description", "Unknown issue"),
            "complaint_type": result.get("category", "other"),
            "complaint_subtype": result.get("sub_category", "other"),
            "authority": result.get("civic_agency", "other"),
            "severity": result.get("severity", "NA"),
            "confidence": result.get("confidence", 50),
            "title": title,
            "description": description,
            "messages": [AIMessage(content="RAG analysis complete.")],
        }
    except Exception:
        return {
            "messages": [AIMessage(content="RAG analysis failed, proceeding without it.")],
        }
