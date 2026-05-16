import uuid
from langchain_core.messages import AIMessage

from civic_redressal.agents.intake.prompt import INTAKE_PROMPT
from civic_redressal.agents.llm.agent import run_text_json_agent, run_vision_json_agent
from civic_redressal.workflow.state import ComplaintState
from civic_redressal.utils.constants import (
    CATEGORY_PROMPT_OPTIONS,
    SUBCATEGORY_PROMPT_OPTIONS,
    CIVIC_AGENCY_PROMPT_OPTIONS,
)
from civic_redressal.utils.util import (
    compute_image_hash,
    find_duplicate_image,
    image_to_base64,
    sanitize_text,
)

def get_prompt(text_content: str) -> str:
    prompt = INTAKE_PROMPT
    prompt = prompt.replace("{CATEGORY_PROMPT_OPTIONS}", CATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace("{SUBCATEGORY_PROMPT_OPTIONS}", SUBCATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace("{CIVIC_AGENCY_PROMPT_OPTIONS}", CIVIC_AGENCY_PROMPT_OPTIONS)
    prompt = prompt.replace("{text_content}", text_content.strip())
    return prompt

def fallback_analysis(text: str,) -> dict:
    print("Fallback to generic civic issue classification.")
    return {
        "description": text,
        "category": "other",
        "sub_category": "other",
        "civic_agency": "other",
        "confidence": 0,
        "severity": "unknown"
    }


def run_intake_agent(state: ComplaintState) -> dict:
    image_path = state.get("image_path")
    title = sanitize_text(state.get("title"))
    description = sanitize_text(state.get("description"))

    has_textinput = bool(title or description)
    has_imageinput = bool(image_path and image_path.strip())

    if has_imageinput:
        duplicate = find_duplicate_image(image_path)
        if duplicate:
            return {
                "complaint_id": None,
                "analysis": "Duplicate image detected",
                "complaint_type": "duplicate",
                "messages": [AIMessage(content=f"Duplicate image found ID {duplicate['complaint_id']}. Skipped.")],
            }

    text_content = ""
    if title:
        text_content += f"Title: {title}\n"
    if description:
        text_content += f"Description: {description}"

    if has_imageinput:
        try:
            base64img = image_to_base64(image_path)
            prompt = get_prompt(text_content)
            analysis = run_vision_json_agent(prompt, base64img, model="gemma4:e4b")

        except Exception:
            print("Vision-based LLM analysis (model=gemma4:e4b) failed, falling back to filename heuristics.")
            print("This may be due to an unsupported image format, an inaccessible image URL, or an issue with the vision model.")
            analysis = fallback_analysis("General civic issue detected from image")

    elif has_textinput:
        try:
            prompt = get_prompt(text_content)
            analysis = run_text_json_agent(prompt, model="llama3.2:3b")

        except Exception:
            print("Text-based LLM analysis (model=llama3.2:3b) failed, proceeding without it.")
            analysis = fallback_analysis("General civic issue detected from text")

    complaint_id = f"COMP{str(uuid.uuid4())[:8].upper()}"
    image_hash = compute_image_hash(image_path) if has_imageinput else None

    return {
        "complaint_id": complaint_id,
        "analysis": analysis.get("description", "Unknown issue"),
        "complaint_type": analysis.get("category", "other"),
        "complaint_subtype": analysis.get("sub_category", "other"),
        "authority": analysis.get("civic_agency", "other"),
        "severity": analysis.get("severity", "low"),
        "confidence": analysis.get("confidence", 50),
        "image_hash": image_hash,
        "title": title,
        "description": description,
        "messages": [AIMessage(content=f"Analysis complete. Type {analysis.get('category', 'other')} ID {complaint_id}")],
    }