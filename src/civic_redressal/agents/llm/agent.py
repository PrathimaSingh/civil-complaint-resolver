import json
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from civic_redressal.agents.caption.prompt import IMAGE_CAPTION_PROMPT
from civic_redressal.utils.util import image_to_base64


def _clean_json_text(content: str) -> str:
    text = (content or "").strip()

    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    elif text.startswith("```"):
        text = text[len("```"):].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text


def _parse_json_response(content: str) -> dict[str, Any]:
    cleaned = _clean_json_text(content)
    print(f"Raw LLM response:\n{content}\n")
    print(f"Cleaned JSON text:\n{cleaned}\n")
    return json.loads(cleaned)


def run_text_json_agent(prompt: str, model: str = "llama3.2:3b", temperature: float = 0.0) -> dict[str, Any]:
    print(f"Running text agent with model {model}...")
    print(f"Prompt:\n{prompt}\n")
    llm = ChatOllama(model=model, temperature=temperature)
    result = llm.invoke([HumanMessage(content=prompt)])
    return _parse_json_response(result.content)


def run_vision_json_agent(
    prompt: str,
    base64_image: str,
    model: str = "gemma4:e4b",
    temperature: float = 0.0,
) -> dict[str, Any]:
    print(f"Running vision agent with model {model}...")
    print(f"Prompt:\n{prompt}\n")
    llm = ChatOllama(model=model, temperature=temperature)
    result = llm.invoke([
        HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ]
        )
    ])
    return _parse_json_response(result.content)

def run_vision_caption_agent(
    image_path: str,
    model: str = "gemma4:e4b",
    temperature: float = 0.0,
) -> dict:
    if not image_path:
        return {
            "caption": None,
            "status": "failed",
            "error": "image_path is required",
        }

    try:
        image_b64 = image_to_base64(image_path)

        llm = ChatOllama(model=model, temperature=temperature)
        result = llm.invoke([
            HumanMessage(
                content=[
                    {"type": "text", "text": IMAGE_CAPTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                ]
            )
        ])

        caption = result.content.strip()

        return {
            "caption": caption,
            "status": "success",
            "model": model,
            "image_path": image_path,
        }

    except Exception as e:
        return {
            "caption": None,
            "status": "failed",
            "error": str(e),
            "model": model,
            "image_path": image_path,
        }
