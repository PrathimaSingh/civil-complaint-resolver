import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from civic_redressal.agents.llm import agent


class DummyResponse:
    def __init__(self, content):
        self.content = content


class DummyLLM:
    def __init__(self, *args, **kwargs):
        pass

    def invoke(self, messages):
        return DummyResponse("A pothole is visible in the road")


def test_run_vision_caption_agent_returns_caption(monkeypatch, tmp_path):
    monkeypatch.setattr(agent, "image_to_base64", lambda image_path: "fake-base64")
    monkeypatch.setattr(agent, "ChatOllama", DummyLLM)

    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake-image")

    result = agent.run_vision_caption_agent(str(image_path))

    assert result["status"] == "success"
    assert result["caption"] == "A pothole is visible in the road"


def test_parse_json_response_recovers_from_missing_closing_brace():
    truncated_response = '{\n  "description": "Test issue",\n  "category": "Pothole"\n'
    parsed = agent._parse_json_response(truncated_response)

    assert parsed["description"] == "Test issue"
    assert parsed["category"] == "Pothole"
