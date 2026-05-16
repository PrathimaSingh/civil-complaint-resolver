import os
import pandas as pd
from urllib.parse import urlparse
import uuid
from langchain_core.messages import AIMessage, HumanMessage
import requests

from civic_redressal.workflow.graphs import (
    app,
    rag_app,
    rag_img_app,
    rag_ingest_app,
    close_app,
)
from civic_redressal.utils.util import is_url


# ====================== PROCESS FUNCTIONS ======================
def process_new_complaint(image_path: str, title: str = None, description: str = None):
    has_text_input = title or description

    if not has_text_input:
        if is_url(image_path):
            try:
                head = requests.head(image_path, timeout=10)
                head.raise_for_status()
            except Exception as e:
                print(f"Image URL not accessible: {image_path} ({e})")
                return
            display_name = os.path.basename(urlparse(image_path).path) or image_path
        else:
            if not os.path.exists(image_path):
                print(f"Image not found: {image_path}")
                return
            display_name = os.path.basename(image_path)
    else:
        display_name = title or description or "Text-based complaint"

    print(f"\n{'=' * 100}")
    print(f"Processing New Complaint: {display_name}")
    print(f"{'=' * 100}")

    inputs = {
        "image_path": image_path,
        "title": title,
        "description": description,
        "messages": [HumanMessage(content="Process new civil complaint")],
    }
    config = {"configurable": {"thread_id": f"thread_{uuid.uuid4().hex[:12]}"}}

    for chunk in app.stream(inputs, config, stream_mode="values"):
        if "messages" in chunk and chunk["messages"]:
            last_msg = chunk["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.content:
                print(f"-- {last_msg.content}")

    print(f"{'=' * 100}\n")


def process_new_complaint_rag(
    title: str,
    description: str,
    image_path: str = "",
    metadata_filter=None,
):
    """Process new complaint using RAG analysis"""
    display_name = title or description or "Text-based complaint"

    print(f"\n{'=' * 100}")
    print(f"Processing New Complaint with RAG: {display_name}")
    print(f"{'=' * 100}")

    inputs = {
        "image_path": image_path,
        "title": title,
        "description": description,
        "messages": [
            HumanMessage(content="Process new civil complaint with RAG analysis")
        ],
    }
    config = {"configurable": {"thread_id": f"thread_{uuid.uuid4().hex[:12]}"}}

    app = rag_img_app if image_path else rag_app
    for chunk in app.stream(inputs, config, stream_mode="values"):
        if "messages" in chunk and chunk["messages"]:
            last_msg = chunk["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.content:
                print(f"-- {last_msg.content}")

    print(f"{'=' * 100}\n")


def ingest_complaints_from_csv(
    csv_path: str,
    title_column: str,
    description_column: str,
    image_column: str,
    category_column: str,
    sub_category_column: str,
    civic_agency_column: str,
):
    df = pd.read_csv(csv_path)
    complaintList = []
    for _, row in df.iloc[:5].iterrows():  # Process first 5 rows as an example
        title = row.get(title_column, "")
        description = row.get(description_column, "")
        image_path = row.get(image_column, "")
        category = row.get(category_column, "")
        print(f"Category column name: {category_column}")
        print(f"Category column value: {category}")
        sub_category = row.get(sub_category_column, "")
        print(f"Sub-category column name: {sub_category_column}")
        print(f"Sub-category column value: {sub_category}")
        civic_agency = row.get(civic_agency_column, "")
        print(f"Civic agency column name: {civic_agency_column}")
        print(f"Civic agency column value: {civic_agency}")

        complaint = {
            "title": title,
            "description": description,
            "image_path": image_path,
            "complaint_type": category,
            "complaint_subtype": sub_category,
            "authority": civic_agency,
            "messages": [HumanMessage(content="Ingest complaint in bulk")],
        }
        complaintList.append(complaint)
    input_data = {"complaints": complaintList}

    config = {"configurable": {"thread_id": f"ingest_{uuid.uuid4().hex[:12]}"}}
    for chunk in rag_ingest_app.stream(input_data, config, stream_mode="values"):
        if "messages" in chunk and chunk["messages"]:
            last_msg = chunk["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.content:
                print(f"-- {last_msg.content}")
    print(f"\n{'=' * 100}")


def close_complaint(complaint_id: str, resolved_image_path: str):
    if not os.path.exists(resolved_image_path):
        print(f"Resolved image not found: {resolved_image_path}")
        return

    inputs = {
        "complaint_id": complaint_id,
        "resolved_image_path": resolved_image_path,
        "messages": [HumanMessage(content="Close complaint")],
    }
    config = {"configurable": {"thread_id": f"close_{complaint_id}"}}

    for chunk in close_app.stream(inputs, config, stream_mode="values"):
        if "messages" in chunk and chunk["messages"]:
            last = chunk["messages"][-1]
            if isinstance(last, AIMessage):
                print(f"-- {last.content}")
