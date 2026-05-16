from langchain_core.messages import AIMessage

from civic_redressal.agents.llm.agent import run_vision_caption_agent
from civic_redressal.workflow.state import ComplaintBatchState, ComplaintState

def run_image_caption_agent(
    state: ComplaintState,
    model: str = "gemma4:e4b",
) -> dict:
    image_path = state.get("image_path")
    if not image_path:
        return {
            "image_caption": None,
            "messages": [AIMessage(content="No image provided for captioning.")],
        }
    result = run_vision_caption_agent(image_path=image_path, model=model)

    return {
        "image_caption": result.get("caption"),
        "messages": [
            AIMessage(
                content=(
                    f"Image caption generated: {result.get('caption')}"
                    if result.get("status") == "success"
                    else f"Image caption failed: {result.get('error')}"
                )
            )
        ],
    }

def run_image_caption_bulk_agent(state: ComplaintBatchState, model: str = "gemma4:e4b") -> dict:
    print(f"Running image captioning for batch of {len(state.get('complaints', []))} complaints...")
    processed_complaints = []
    for complaint in state.get("complaints", []):
        if not complaint.get("image_path"):
            print(f"No image for complaint '{complaint.get('title', 'N/A')}', skipping captioning.")
            complaint_with_caption = {**complaint, "image_caption": None}
            processed_complaints.append(complaint_with_caption)
            continue
        caption_result = run_image_caption_agent(complaint, model=model)
        print(f"Caption result for complaint '{complaint.get('title', 'N/A')}': {caption_result.get('image_caption')}")
        complaint_with_caption = {**complaint, **caption_result}
        processed_complaints.append(complaint_with_caption)
    return {
        "complaints": processed_complaints
    }