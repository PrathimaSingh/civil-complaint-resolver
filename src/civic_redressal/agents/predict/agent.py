import csv
import uuid
from langchain_core.messages import AIMessage

from civic_redressal.agents.llm.agent import (
    run_text_json_agent,
    run_vision_caption_agent,
    run_vision_json_agent,
)
from civic_redressal.agents.predict.prompt import (
    IMAGE_PREDICTION_PROMPT,
    RETRIEVAL_RAG_PROMPT,
    TEXT_PREDICTION_PROMPT,
)
from civic_redressal.utils.constants import (
    CATEGORY_PROMPT_OPTIONS,
    SUBCATEGORY_PROMPT_OPTIONS,
    CIVIC_AGENCY_PROMPT_OPTIONS,
)
from civic_redressal.utils.util import image_to_base64, is_url, sanitize_text
from civic_redressal.workflow.state import (
    ComplaintPredictionBatchState,
    ComplaintPredictionState,
)


def run_prediction_llm_agent(state: ComplaintPredictionState) -> dict:
    similar_complaints = state.get("similar_complaints") or ""
    title = sanitize_text(state.get("title"))
    description = sanitize_text(state.get("description"))

    prompt = RETRIEVAL_RAG_PROMPT
    prompt = prompt.replace("{CATEGORY_PROMPT_OPTIONS}", CATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace("{SUBCATEGORY_PROMPT_OPTIONS}", SUBCATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace(
        "{CIVIC_AGENCY_PROMPT_OPTIONS}", CIVIC_AGENCY_PROMPT_OPTIONS
    )
    prompt = prompt.replace("{similar_complaints}", similar_complaints)
    prompt = prompt.replace("{title}", title)
    prompt = prompt.replace("{description}", description)
    try:
        result = run_text_json_agent(prompt, model="llama3.2:3b")
        complaint_id = f"COMP{str(uuid.uuid4())[:8].upper()}"

        return {
            "complaint_id": complaint_id,
            "title": title,
            "description": description,
            "predicted_description": result.get("description", "Unknown issue"),
            "predicted_category": result.get("category", "other"),
            "predicted_sub_category": result.get("sub_category", "other"),
            "predicted_civic_agency": result.get("civic_agency", "other"),
            "predicted_severity": result.get("severity", "NA"),
            "predicted_confidence": result.get("confidence", 50),
            "messages": [AIMessage(content="Prediction RAG analysis complete.")],
        }
    except Exception:
        return {
            "complaint_id": "unknown",
            "title": title,
            "description": description,
            "predicted_description": "Unknown issue",
            "predicted_category": "other",
            "predicted_sub_category": "other",
            "predicted_civic_agency": "other",
            "predicted_severity": "NA",
            "predicted_confidence": 0,
            "messages": [
                AIMessage(
                    content="Prediction RAG analysis failed, proceeding without it."
                )
            ],
        }


def save_prediction_result(result: list):
    # Placeholder for saving the prediction result to a database or file
    print(f"Saving prediction results for {len(result)} complaints.")
    # saving to csv
    with open("results/post_ingestion_prediction_results.csv", "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=result[0].keys() if result else [])
        writer.writeheader()
        writer.writerows(result)


def run_bulk_prediction_rag_agent(state: ComplaintPredictionBatchState) -> dict:
    print(
        f"Running prediction for batch of {len(state.get('complaints', []))} complaints..."
    )
    print(
        "prediction agent - validation file path: ", state.get("validation_file_path")
    )
    processed_complaints = []
    for i, complaint in enumerate(state.get("complaints", [])):
        print(
            f"Processing complaint {i + 1}/{len(state.get('complaints', []))}: '{complaint.get('title', 'N/A')}'"
        )
        result = run_prediction_llm_agent(complaint)
        # print(f"Prediction result for complaint '{complaint.get('title', 'N/A')}': {result.get('predicted_description', 'N/A')} | Predicted Type: {result.get('predicted_category', 'N/A')} \
        #       | Predicted Subtype: {result.get('predicted_sub_category', 'N/A')} | Predicted Authority: {result.get('predicted_civic_agency', 'N/A')}")
        processed_complaints.append(result)
    save_prediction_result(processed_complaints)
    return {**state, "complaints": processed_complaints}


def get_text_prompt(text_content: str) -> str:
    prompt = TEXT_PREDICTION_PROMPT
    prompt = prompt.replace("{CATEGORY_PROMPT_OPTIONS}", CATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace("{SUBCATEGORY_PROMPT_OPTIONS}", SUBCATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace(
        "{CIVIC_AGENCY_PROMPT_OPTIONS}", CIVIC_AGENCY_PROMPT_OPTIONS
    )
    prompt = prompt.replace("{text_content}", text_content.strip())
    return prompt


def get_image_prompt(text_content: str) -> str:
    prompt = IMAGE_PREDICTION_PROMPT
    prompt = prompt.replace("{CATEGORY_PROMPT_OPTIONS}", CATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace(
        "{CIVIC_AGENCY_PROMPT_OPTIONS}", CIVIC_AGENCY_PROMPT_OPTIONS
    )
    prompt = prompt.replace("{text_content}", text_content.strip())
    return prompt


def run_bulk_prediction_agent(state: ComplaintPredictionBatchState) -> dict:
    print(
        f"Running prediction for batch of {len(state.get('complaints', []))} complaints without RAG..."
    )
    processed_complaints = []
    for i, complaint in enumerate(state.get("complaints", [])):
        title = sanitize_text(complaint.get("title", ""))
        description = sanitize_text(complaint.get("description", ""))
        image_path = complaint.get("image_path")

        print("image_path: ", image_path)

        has_textinput = bool(title or description)
        has_imageinput = bool(image_path and image_path.strip())

        text_content = ""
        if title:
            text_content += f"Title: {title}\n"
        if description:
            text_content += f"Description: {description}"

        fallback_result = {
            "complaint_id": f"COMP{str(uuid.uuid4())[:8].upper()}",
            "title": title,
            "description": description,
            "image_path": image_path,
            "predicted_description": "Unknown issue",
            "predicted_category": "other",
            "predicted_sub_category": "other",
            "predicted_civic_agency": "other",
            "predicted_severity": "NA",
            "predicted_confidence": 0,
            "messages": [
                AIMessage(content="Prediction analysis failed, proceeding without it.")
            ],
        }
        result = fallback_result

        if has_imageinput:
            print(
                f"Image path for complaint '{complaint.get('title', 'N/A')}': {image_path}"
            )
            try:
                base64img = image_to_base64(image_path)
                prompt = get_image_prompt(text_content)
                llm_result = run_vision_json_agent(prompt=prompt, base64_image=base64img)
                complaint_id = f"COMP{str(uuid.uuid4())[:8].upper()}"

                result = {
                    "complaint_id": complaint_id,
                    "title": title,
                    "description": description,
                    "image_path": image_path,
                    "predicted_description": llm_result.get("description", "Unknown issue"),
                    "predicted_category": llm_result.get("category", "other"),
                    "predicted_civic_agency": llm_result.get("civic_agency", "other"),
                    "predicted_severity": llm_result.get("severity", "NA"),
                    "predicted_confidence": llm_result.get("confidence", 50),
                    "messages": [
                        AIMessage(content="Prediction RAG analysis complete.")
                    ],
                }
            except Exception as e:
                print(
                    f"Error occurred while processing image for complaint '{complaint.get('title', 'N/A')}': {e}"
                )
                result = fallback_result
        elif has_textinput:
            print(
                f"No image path provided for complaint '{complaint.get('title', 'N/A')}' but text is available."
            )
            try:
                prompt = get_text_prompt(text_content)
                llm_result = run_text_json_agent(prompt)
                complaint_id = f"COMP{str(uuid.uuid4())[:8].upper()}"

                result = {
                    "complaint_id": complaint_id,
                    "title": title,
                    "description": description,
                    "image_path": image_path,
                    "predicted_description": llm_result.get("description", "Unknown issue"),
                    "predicted_category": llm_result.get("category", "other"),
                    "predicted_sub_category": llm_result.get("sub_category", "other"),
                    "predicted_civic_agency": llm_result.get("civic_agency", "other"),
                    "predicted_severity": llm_result.get("severity", "NA"),
                    "predicted_confidence": llm_result.get("confidence", 50),
                    "messages": [AIMessage(content="Prediction RAG analysis complete.")],
                }
            except Exception as e:
                print(
                    f"Error occurred while processing text for complaint '{complaint.get('title', 'N/A')}': {e}"
                )
                result = fallback_result

        processed_complaints.append(result)
    save_prediction_result(processed_complaints)
    return {**state, "complaints": processed_complaints}
