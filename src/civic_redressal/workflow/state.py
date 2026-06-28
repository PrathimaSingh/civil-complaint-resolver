
from typing import List, TypedDict, Sequence, Annotated
from operator import add

class ComplaintState(TypedDict):
    image_path: str
    complaint_id: str | None
    analysis: str | None
    complaint_type: str | None
    complaint_subtype: str | None
    severity: str | None
    confidence: int | None
    authority: str | None
    complaint_message: str | None
    status: str | None
    resolved_image_path: str | None
    image_hash: str | None
    image_caption: str | None
    messages: Annotated[Sequence, add]
    analytics: dict | None
    title: str | None  # Optional textual title
    description: str | None  # Optional textual description
    similar_complaints: str | None  # RAG context of similar complaints

class ComplaintBatchState(TypedDict):
    complaints: List[ComplaintState]

class ComplaintPredictionState(TypedDict):
    complaint_id: str | None
    title: str | None
    description: str | None
    image_path: str
    predicted_description: str | None
    predicted_category: str | None
    predicted_sub_category: str | None
    predicted_civic_agency: str | None
    predicted_severity: str | None
    predicted_confidence: int | None
    similar_complaints: str | None  # RAG context of similar complaints
    messages: Annotated[Sequence, add]

class ComplaintPredictionBatchState(TypedDict):
    complaints: List[ComplaintPredictionState]
    test_file_path: str
    validation_file_path: str
    prediction_analytics: dict | None
    messages: Annotated[Sequence, add]