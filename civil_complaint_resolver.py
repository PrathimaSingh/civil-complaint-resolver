# ========================================================
# CIVIL COMPLAINT RESOLVER - FIXED VERSION (with Proper Routing)
# ========================================================

import os
import re
import uuid
import json
import base64
from datetime import datetime
from typing import Annotated, TypedDict, Sequence
from operator import add
from collections import defaultdict
import requests
from io import BytesIO
from urllib.parse import urlparse
import msvcrt

from PIL import Image
import imagehash

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Vector DB imports (assuming this file exists)
from complaint_vector_db import retrieve_top_k_complaints, store_complaint, search_complaints, list_all_complaints

print("=== Civil Complaint Resolver - Fixed Routing + Better Analytics ===\n")

# ========================= CONFIG =========================
INCOMING_FOLDER = "./incoming_complaints"
RESOLVED_FOLDER = "./resolved_complaints"
SENT_MESSAGES_FOLDER = "./sent_messages"
PROMPT_FOLDER = "./prompts"
PROMPT_NUMBER = 1
COMPLAINTS_DB_FILE = "complaints_db.json"

CATEGORY_CHOICES = [
    "Animal Husbandry",
    "Certificates",
    "Community Infrastructure and Services",
    "Crime and Safety",
    "Electricity and Power Supply",
    "Garbage and Unsanitary Practices",
    "Lakes",
    "Mobility - Roads, Footpaths and Infrastructure",
    "Mobility - Roads, Public transport",
    "Parks & Recreation",
    "Pollution",
    "Public Toilets",
    "Sewerage Systems",
    "Storm Water Drains",
    "Street lighting",
    "Streetlights",
    "Traffic and Road Safety",
    "Water Supply",
    "Water Supply and Services",
    "Yellow Spot",
]
CATEGORY_PROMPT_OPTIONS = " | ".join(CATEGORY_CHOICES) + " | other"

SUBCATEGORY_CHOICES = [
    "1B- Require New Public Toilet",
    "2A- Require New Footpath",
    "2B- Repair Broken Footpath",
    "2C- Remove Garbage or Debris on Footpath",
    "Air Pollution",
    "Build Dry Waste Collection Centre",
    "Certificates - Other",
    "Clearance Of Garbage Dump Or Black Spot",
    "Collection Of Door-to-door Garbage",
    "Construction Of Educational Institutions And Libraries",
    "Construction Of New Public Toilet",
    "Construction Of Roadside Drains",
    "Construction Of Sewage Lines",
    "Construction of flyovers/ underpass",
    "Construction of new footpaths",
    "Controlling Of Stray Cattle Or Maintenance Of Cattle Pound",
    "Desilting Existing Roadside Drains",
    "Desilting/Remove Blockage of Storm Water Drains",
    "Encroachment of cycle lane",
    "Eve Teasing/Public Nuisance",
    "Fixing/Reparing Potholes",
    "Flooding/Waterlogging Of Roads And Footpaths",
    "Fogging (Mosquito Menace) Or Pest Control",
    "Garbage Dumping In Vacant Lot/Land",
    "Installation Of New Streetlights",
    "Installation Of Traffic or Pedestrain Lights",
    "Installation/Maintenance Of Streetlight Timer",
    "Maintenance And Repair Of Manholes",
    "Maintenance And Repair Of Sewage Lines",
    "Maintenance And Repair Of Storm Water Drains",
    "Maintenance Of Lake Surrounding",
    "Maintenance Of Shopping And Commercial Complexes",
    "Maintenance Of existing Parks",
    "Maintenance/Repair Of Streetlights",
    "Management Of Hawkers and Vendors",
    "Need Covering Slabs For Roadside Drains",
    "Need Lane Markings/Street Name/Road Signages",
    "Noise Pollution",
    "One Way/No Entry",
    "Property Tax",
    "Reduce water leakage and wastage",
    "Regular Supply Of Electricity",
    "Regular Water Supply",
    "Removal Of Illegal Posters And Hoardings",
    "Removal Of Roadside Debris (Construction Material)",
    "Repair Of Existing Footpaths",
    "Report A Broken Footpath",
    "Report A Public Urination or Yellow Spot",
    "Report Garbage or Debris on Footpath",
    "Require A New Footpath",
    "Require A New Public Toilet",
    "Riding On Footpath",
    "Stop Water Leakage",
    "Stray Dog Sterilisation/Animal Birth Control (ABC)",
    "Tarring Or Asphalting Of Existing Road",
    "Tarring Or Asphalting Of Mud/Kutcha/Unpaved Road",
    "Traffic Jams/Congestion Or Bottlenecks",
    "Violating lane discipline",
]
SUBCATEGORY_PROMPT_OPTIONS = " | ".join(SUBCATEGORY_CHOICES) + " | other"

CIVIC_AGENCY_CHOICES = [
    "BBMP",
    "BCP",
    "BDA",
    "BESCOM",
    "BTP",
    "BWSSB",
    "KSPCB",
]
CIVIC_AGENCY_PROMPT_OPTIONS = " | ".join(CIVIC_AGENCY_CHOICES) + " | other"

CATEGORY_CIVIC_AGENCY_MAP = {
    "BBMP": ["Animal Husbandry", "Certificates", "Community Infrastructure and Services", "Garbage and Unsanitary Practices", "Lakes", 
             "Mobility - Roads, Footpaths and Infrastructure", "Parks & Recreation", "Public Toilets", "Storm Water Drains", 
             "Street lighting", "Streetlights", "Yellow Spot"],
    "BTP": ["Traffic and Road Safety"],
    "BESCOM": ["Electricity and Power Supply"],
    "BWSSB": ["Sewerage Systems", "Water Supply", "Water Supply and Services"],
    "KSPCB": ["Pollution"],
    "BDA": ["Mobility - Roads, Public transport"],
    "BCP": ["Crime and Safety"],
}

# Create folders
os.makedirs(INCOMING_FOLDER, exist_ok=True)
os.makedirs(RESOLVED_FOLDER, exist_ok=True)
os.makedirs(SENT_MESSAGES_FOLDER, exist_ok=True)
os.makedirs(PROMPT_FOLDER, exist_ok=True)

# ====================== JSON DB ======================
def load_complaints_db() -> dict:
    if os.path.exists(COMPLAINTS_DB_FILE):
        with open(COMPLAINTS_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_complaints_db(db: dict):
    with open(COMPLAINTS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

complaints_db = load_complaints_db()

# ====================== STATE ======================
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
    messages: Annotated[Sequence, add]
    analytics: dict | None
    complaint_title: str | None  # Optional textual title
    complaint_description: str | None  # Optional textual description
    similar_complaints: str | None  # RAG context of similar complaints

memory = MemorySaver()

# ====================== HELPERS ======================
def is_url(path: str) -> bool:
    """Check if path is a URL"""
    return path.startswith(("http://", "https://"))

def image_to_base64(image_path: str) -> str:
    """Convert image to base64, supporting both URLs and local files"""
    try:
        if is_url(image_path):
            response = requests.get(image_path, timeout=10)
            response.raise_for_status()
            return base64.b64encode(response.content).decode("utf-8")
        else:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"Error converting image to base64: {e}")
        return ""

def sanitize_text(text, keep_punctuation=False, keep_numbers=True, keep_hyphens=True):
    """
    Sanitize text by removing special characters.
    
    Args:
        text: Input text to sanitize
        keep_punctuation: Keep common punctuation (.,!?;:-)
        keep_numbers: Keep digits 0-9
        keep_hyphens: Keep hyphens (useful for compound words)
    
    Returns:
        Cleaned text with special characters removed
    """
    if not text:
        return ""
    
    # Base pattern: letters, spaces, and optionally numbers/hyphens
    allowed_chars = r'a-zA-Z\s'
    
    if keep_numbers:
        allowed_chars += r'0-9'
    
    if keep_hyphens:
        allowed_chars += r'-'
    
    if keep_punctuation:
        allowed_chars += r'.,!?;:-'
    
    # Remove all characters NOT in allowed set (global, case-insensitive)
    cleaned = re.sub(f'[^ {allowed_chars}]', '', text)
    
    # Multiple spaces to single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned

def read_multiline_description(prompt: str = "Enter complaint description. Press ESC to finish.") -> str:
    print(prompt)
    print("(Press Enter for new line, then ESC when done)")
    lines = []
    current = []

    while True:
        ch = msvcrt.getwch()
        if ch == "\x1b":  # ESC
            print()
            break
        if ch == "\r":
            print()
            lines.append("".join(current))
            current = []
            continue
        if ch == "\x08":  # Backspace
            if current:
                current.pop()
                print("\b \b", end="", flush=True)
            continue
        current.append(ch)
        print(ch, end="", flush=True)

    if current:
        lines.append("".join(current))
    return "\n".join(lines).strip()

def compute_image_hash(image_path: str) -> str:
    """Compute image hash, supporting both URLs and local files"""
    try:
        if is_url(image_path):
            response = requests.get(image_path, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content)).convert("L")
        else:
            img = Image.open(image_path).convert("L")
        
        phash = str(imagehash.phash(img))
        dhash = str(imagehash.dhash(img))
        return f"{phash}|{dhash}"
    except Exception as e:
        print(f"Hash error: {e}")
        return ""

def find_duplicate_image(new_image_path: str) -> dict | None:
    new_hash_str = compute_image_hash(new_image_path)
    if not new_hash_str:
        return None

    db = load_complaints_db()
    for cid, data in db.items():
        if "image_hash" not in data or not data["image_hash"]:
            continue
        try:
            ph_new, dh_new = new_hash_str.split("|")
            ph_old, dh_old = data["image_hash"].split("|")
            dist_ph = imagehash.hex_to_hash(ph_new) - imagehash.hex_to_hash(ph_old)
            dist_dh = imagehash.hex_to_hash(dh_new) - imagehash.hex_to_hash(dh_old)

            if dist_ph <= 8 or dist_dh <= 6:
                return {
                    "complaint_id": cid,
                    "image_path": data.get("image_path"),
                    "distance": min(int(dist_ph), int(dist_dh))
                }
        except:
            continue
    return None

def display_image(image_path: str):
    """Display image or show image URL"""
    if is_url(image_path):
        print(f"Displaying Image from URL: {image_path}")
        print(f"-- Image accessible at: {image_path}")
    else:
        print(f"Displaying Image: {os.path.basename(image_path)}")
        try:
            img = Image.open(image_path)
            img.show()
            print("-- Image opened in default viewer")
        except Exception as e:
            print(f"-- Could not open viewer: {e}")

def read_prompt(prompt_path):
    with open(prompt_path, 'r') as file:
        return file.read().strip()

def format_context(retrieved_complaints):
    """Format retrieved complaints as LLM context."""
    context_parts = []
    
    for i, complaint in enumerate(retrieved_complaints, 1):
        context_parts.append(
            f"""Complaint #{i} (Similarity score: {complaint['score']})
Title: {complaint['title']}
Description: {complaint['description']}
Category: {complaint['category']}
Subcategory: {complaint['sub_category']}
Agency: {complaint['civic_agency']}"""
        )
    
    return "\n\n".join(context_parts)

# ====================== NODES ======================
def retrieval_node(state: ComplaintState, top_k=5, metadata_filter=None):
    """
    Retrieve similar complaints from Vector DB based on image and/or text
    RAG pipeline: Retrieve similar complaints → Feed to Llama → Predict labels.
    """

    # 1. Retrieve top-k similar complaints
    retrieved = retrieve_top_k_complaints(
        title=state.get("complaint_title", "") or "",
        description=state.get("complaint_description", "") or "",
        top_k=top_k,
        metadata_filter=metadata_filter
    )

    # print(f"Retrieval Node - Retrieved {len(retrieved)} complaints from vector DB for RAG context.")
    # print(f"Top retrieved complaint (if any): {retrieved[0]['title'] if retrieved else 'None'}")
    # print(f"Retrieval Node - Retrieved complaints: {[c['score'] for c in retrieved]}")
    # print(f"Similarity scores of retrieved complaints: {[c['score'] for c in retrieved]}")

    # 2. Format context
    context = format_context(retrieved)

    print(f"Retrieval Node - Found {len(retrieved)} similar complaints")
    print("Retrieval Node - Similar complaints for RAG context:")
    for i, complaint in enumerate(retrieved, 1):
        print(f"  {i}. {complaint['title']} (Score: {complaint['score']})")
    print(f"Retrieval Node - Formatted context for RAG:\n{context[:500]}...\n")

    return {
        "similar_complaints": context,
        "messages": [AIMessage(content=f"Retrieved {len(retrieved)} similar complaints for reference.")]
    }

def rag_llm_node(state: ComplaintState):
    """LLM node that takes retrieved complaints as context and predicts labels"""
    from langchain_ollama import ChatOllama

    similar_complaints = state.get("similar_complaints", "")
    complaint_title = sanitize_text(state.get("complaint_title"))
    complaint_description = sanitize_text(state.get("complaint_description"))

    print("similar_complaints content for RAG LLM Node:")
    print(similar_complaints)
    print("RAG LLM Node - Preparing prompt with retrieved complaints and input data...")

    prompt = read_prompt(f"{PROMPT_FOLDER}/prompt_rag.txt")
    prompt = prompt.replace("{CATEGORY_PROMPT_OPTIONS}", CATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace("{SUBCATEGORY_PROMPT_OPTIONS}", SUBCATEGORY_PROMPT_OPTIONS)
    prompt = prompt.replace("{CIVIC_AGENCY_PROMPT_OPTIONS}", CIVIC_AGENCY_PROMPT_OPTIONS)
    prompt = prompt.replace("{similar_complaints}", similar_complaints)
    prompt = prompt.replace("{complaint_title}", complaint_title)
    prompt = prompt.replace("{complaint_description}", complaint_description)

    print(f"RAG LLM Prompt:\n{prompt}\n")

    try:
        rag_llm = ChatOllama(model="llama3.2:3b", temperature=0.0)
        message = HumanMessage(content=prompt)
        result = rag_llm.invoke([message])
        content = result.content.strip()
        print(f"RAG LLM Output: {content[:200]}...")

        result = json.loads(content)
        print(f"RAG LLM Parsed Result - Type: {result.get('category')} | Subtype: {result.get('sub_category')} | Agency: {result.get('civic_agency')} | Severity: {result.get('severity')} | Confidence: {result.get('confidence')}")

        complaint_id = f"COMP{str(uuid.uuid4())[:8].upper()}"

        return {
            "rag_analysis": content, 
            "complaint_id": complaint_id,
            "analysis": result.get("description", "Unknown issue"),
            "complaint_type": result.get("category", "other"),
            "complaint_subtype": result.get("sub_category", "other"),
            "authority": result.get("civic_agency", "other"),
            "severity": result.get("severity", "N/A"),
            "confidence": result.get("confidence", 50),
            # "image_hash": image_hash,
            "complaint_title": complaint_title,
            "complaint_description": complaint_description,
            "messages": [AIMessage(content="RAG analysis complete.")]
        }

    except Exception as e:
        print(f"RAG LLM error: {e}")
        return {"rag_analysis": "", "messages": [AIMessage(content="RAG analysis failed, proceeding without it.")]}

def analyzer_node(state: ComplaintState):
    """Analyze image with improved prompt, optionally using textual inputs"""
    from langchain_ollama import ChatOllama

    image_path = state["image_path"]
    complaint_title = sanitize_text(state.get("complaint_title"))
    complaint_description = sanitize_text(state.get("complaint_description"))

    # Check if we have textual inputs
    has_text_input = bool(complaint_title or complaint_description)
    # Check if we have an image input
    has_image_input = bool(image_path and image_path.strip())

    # Duplicate Check (only for images)
    if has_image_input:
        print("Checking for duplicate image using perceptual hashing...")
        duplicate = find_duplicate_image(image_path)

        if duplicate:
            print(f"DUPLICATE IMAGE DETECTED! Similar to Complaint: {duplicate['complaint_id']}")
            return {
                "complaint_id": None,
                "analysis": "Duplicate image detected",
                "complaint_type": "duplicate",
                "messages": [AIMessage(content=f"Duplicate image found (ID: {duplicate['complaint_id']}). Skipped.")]
            }
    
    text_content = ""
    if has_text_input:
        if complaint_title:
            text_content += f"Title: {complaint_title}\n"
        if complaint_description:
            text_content += f"Description: {complaint_description}\n"

    # Build analysis prompt based on available inputs
    if has_text_input and not has_image_input:
        # Text-based analysis
        print("Analyzing complaint using provided text input...")

        # Use text analysis model
        try:
            text_llm = ChatOllama(model="llama3.2:3b", temperature=0.0)

            prompt = read_prompt(f"{PROMPT_FOLDER}/prompt{PROMPT_NUMBER}.txt")
            prompt = prompt.replace("{CATEGORY_PROMPT_OPTIONS}", CATEGORY_PROMPT_OPTIONS)
            prompt = prompt.replace("{SUBCATEGORY_PROMPT_OPTIONS}", SUBCATEGORY_PROMPT_OPTIONS)
            prompt = prompt.replace("{CIVIC_AGENCY_PROMPT_OPTIONS}", CIVIC_AGENCY_PROMPT_OPTIONS)
            prompt = prompt.replace("{text_content}", text_content.strip())

            print(f"Text Analysis Prompt:\n{prompt}\n")

            message = HumanMessage(content=prompt)
            result = text_llm.invoke([message])
            content = result.content.strip()

        except Exception as e:
            print(f"Text analysis model not available ({e}), using fallback")
            # Fallback analysis based on keywords
            text_combined = (complaint_title or "") + " " + (complaint_description or "")
            text_lower = text_combined.lower()

            if any(word in text_lower for word in ["garbage", "waste", "trash", "rubbish"]):
                analysis = {"description": complaint_description or complaint_title or "Garbage issue", "category": "Garbage and Unsanitary Practices", "sub_category": "other", "confidence": 70, "severity": "medium"}
            elif any(word in text_lower for word in ["road", "pothole", "crack", "damage", "hole"]):
                analysis = {"description": complaint_description or complaint_title or "Road damage issue", "category": "Mobility - Roads, Footpaths and Infrastructure", "sub_category": "pothole", "confidence": 70, "severity": "high"}
            elif any(word in text_lower for word in ["light", "streetlight", "lamp", "electricity", "power"]):
                analysis = {"description": complaint_description or complaint_title or "Street light issue", "category": "Streetlights", "sub_category": "not working", "confidence": 70, "severity": "medium"}
            else:
                analysis = {"description": complaint_description or complaint_title or "General civic issue", "category": "other", "sub_category": "other", "confidence": 50, "severity": "low"}

    else:
        # Image-based analysis (existing logic)
        print("Analyzing complaint using image...")
        try:
            vision_llm = ChatOllama(model="gemma4:e4b", temperature=0.0)
            base64_img = image_to_base64(image_path)

            prompt = f"""You are an expert civic complaint analyzer for Bengaluru city.
Analyze the image and return ONLY valid JSON with these exact keys:
{{
  "description": "Clear one-sentence description of the issue",
  "complaint_type": "{CATEGORY_PROMPT_OPTIONS}",
  "complaint_subtype": "{SUBCATEGORY_PROMPT_OPTIONS}",
  "authority": "{CIVIC_AGENCY_PROMPT_OPTIONS}",
  "confidence": complaint_type complaint_subtype and authority prediction confidence in the range 0 to 100,
  "severity": "low | medium | high"
}}
Use only these complaint_type values from the list above.
Do not add any extra text or explanation.

Complaint Text:
{text_content}"""

            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                ]
            )

            result = vision_llm.invoke([message])
            content = result.content.strip()
            print(f"Vision Model Raw Output: {content[:200]}...")

        except Exception as e:
            print(f"Vision model not available ({e}), using basic image analysis")
            # Fallback for image analysis
            filename = os.path.basename(image_path).lower() if not is_url(image_path) else "image"
            if "garbage" in filename or "waste" in filename:
                analysis = {"description": "Garbage issue detected from image", "category": "Garbage and Unsanitary Practices", "sub_category": "other", "confidence": 60, "severity": "medium"}
            elif "road" in filename or "pothole" in filename:
                analysis = {"description": "Road damage detected from image", "category": "Mobility - Roads, Footpaths and Infrastructure", "sub_category": "pothole", "confidence": 60, "severity": "high"}
            elif "light" in filename or "street" in filename:
                analysis = {"description": "Street light issue detected from image", "category": "Streetlights", "sub_category": "not working", "confidence": 60, "severity": "medium"}
            else:
                analysis = {"description": "General civic issue detected from image", "category": "other", "sub_category": "other", "confidence": 50, "severity": "low"}

    # Parse the analysis result
    if 'analysis' not in locals():
        try:
            # Strip markdown code blocks if present (```json ... ```)
            if content.startswith("```"):
                content = content.lstrip("`").lstrip("json").lstrip("JSON").strip()
                if content.endswith("```"):
                    content = content[:-3].strip()

            analysis = json.loads(content)
            print(f"Model returned - Analysis: {analysis.get('description')} | Type: {analysis.get('category')} | Subtype: {analysis.get('sub_category')} | Authority: {analysis.get('civic_agency')} | Severity: {analysis.get('severity')} | Confidence: {analysis.get('confidence')}")
        except Exception as parse_error:
            print(f"Failed to parse JSON: {parse_error}")
            analysis = {"description": content[:300], "category": "other", "sub_category": "other", "confidence": 50, "severity": "low"}

    complaint_id = f"COMP{str(uuid.uuid4())[:8].upper()}"
    image_hash = compute_image_hash(image_path) if not has_text_input else ""

    print(f"New Complaint ID Generated: {complaint_id}")
    if not has_text_input:
        display_image(image_path)

    return {
        "complaint_id": complaint_id,
        "analysis": analysis.get("description", "Unknown issue"),
        "complaint_type": analysis.get("category", "other"),
        "complaint_subtype": analysis.get("sub_category", "other"),
        "authority": analysis.get("civic_agency", "other"),
        "severity": analysis.get("severity", "N/A"),
        "confidence": analysis.get("confidence", 50),
        "image_hash": image_hash,
        "complaint_title": complaint_title,
        "complaint_description": complaint_description,
        "messages": [AIMessage(content=f"Analysis complete. Type: {analysis.get('category')} | ID: {complaint_id}")]
    }


def router_node(state: ComplaintState):
    """Improved routing logic"""
    if state.get("complaint_type") == "duplicate":
        return {"authority": None, "messages": [AIMessage(content="Duplicate - No routing")]}

    ctype = str(state.get("complaint_type", "")).strip()

    print(f"Routing based on complaint type: '{ctype}'")

    if ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BBMP", []):
        actual_authority = "BBMP"
    elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BESCOM", []):
        actual_authority = "BESCOM"
    elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BWSSB", []):
        actual_authority = "BWSSB"
    elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BCP", []):
        actual_authority = "BCP"
    elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BTP", []):
        actual_authority = "BTP"
    elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("KSPCB", []):
        actual_authority = "KSPCB"
    elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BDA", []):
        actual_authority = "BDA"
    else:
        actual_authority = "Other"

    model_authority = state.get("authority", "other")
    if model_authority and model_authority != actual_authority:
        print(f"⚠️ Model predicted authority '{model_authority}' does not match routing logic '{actual_authority}' for category '{ctype}'. Using routing logic authority.")
    else:
        print(f"Model predicted authority '{model_authority}' matches routing logic '{actual_authority}' for category '{ctype}'.")
    

    print(f"Routing Decision: '{ctype}' → {actual_authority}")

    return {
        "authority": actual_authority,
        "messages": [AIMessage(content=f"Routed to -- {actual_authority} (Category: {ctype})")]
    }


def create_complaint(state: ComplaintState, authority: str):
    """Common function to create complaint for any department"""
    if not state.get("complaint_id"):
        return {"messages": [AIMessage(content="Registration skipped due to duplicate")]}

    complaint_id = state["complaint_id"]

    message_text = f"""NEW CIVIL COMPLAINT
Complaint ID     : {complaint_id}
Complaint Title  : {state.get('complaint_title', 'N/A')}
Complaint Desc   : {state.get('complaint_description', 'N/A')}
Category         : {state.get('complaint_type', 'N/A')}
Analysis         : {state.get('analysis', 'N/A')}
Civic Agency     : {authority}
Submitted Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Image Location   : {state['image_path']}

Please take necessary action at the earliest.
"""

    msg_path = f"{SENT_MESSAGES_FOLDER}/{complaint_id}.txt"
    with open(msg_path, "w", encoding="utf-8") as f:
        f.write(message_text)

    complaints_db[complaint_id] = {
        "title": state.get("complaint_title"),
        "description": state.get("complaint_description"),
        "type": state.get("complaint_type"),
        "subtype": state.get("complaint_subtype"),
        "analysis": state.get("analysis"),
        "severity": state.get("severity"),
        "confidence": state.get("confidence"),
        "authority": authority,
        "status": "open",
        "image_path": state["image_path"],
        "image_hash": state.get("image_hash"),
        "resolved_image_path": None,
        "created_at": datetime.now().isoformat(),
        "closed_at": None,
        "message_path": msg_path
    }
    save_complaints_db(complaints_db)

    print(f"✅ Complaint {complaint_id} successfully registered and sent to {authority}")
    return {
        "complaint_message": message_text,
        "status": "open",
        "messages": [AIMessage(content=f"Complaint {complaint_id} created for {authority}")]
    }


def creator_bbmp(state: ComplaintState):
    return create_complaint(state, "BBMP")

def creator_bescom(state: ComplaintState):
    return create_complaint(state, "BESCOM")

def creator_bwssb(state: ComplaintState):
    return create_complaint(state, "BWSSB")

def creator_kspcb(state: ComplaintState):
    return create_complaint(state, "KSPCB")

def creator_bcp(state: ComplaintState):
    return create_complaint(state, "BCP")

def creator_btp(state: ComplaintState):
    return create_complaint(state, "BTP")

def creator_bda(state: ComplaintState):
    return create_complaint(state, "BDA")

def creator_other(state: ComplaintState):
    return create_complaint(state, "Other")


def storage_node(state: ComplaintState):
    if not state.get("complaint_id"):
        return {"messages": [AIMessage(content="Skipped storage due to duplicate")]}
    try:
        print(f"Storing complaint: {state['complaint_id']}")
        print(f"Description: {state.get('complaint_description')}")
        print(f"Analysis: {state.get('analysis')}")
        docid = store_complaint(
            complaint_id=state["complaint_id"],
            title=state.get("complaint_title"),
            description=state.get("complaint_description"),
            category=state.get("complaint_type"),
            sub_category=state.get("complaint_subtype"),
            analysis=state.get("analysis"),
            civic_agency=state.get("authority"),
            status=state.get("status", "open"),
            severity=state.get("severity"),
            confidence=state.get("confidence"),
            image_path=state["image_path"],
            image_hash=state.get("image_hash", "")
        )
        print(f"Complaint stored in Vector DB with docid: {docid}")
        # store_complaint_image(
        #     image_path=state["image_path"],
        #     complaint_id=state["complaint_id"],
        #     complaint_title=state.get("complaint_title"),
        #     complaint_description=state.get("complaint_description"),
        #     complaint_type=state.get("complaint_type"),
        #     complaint_subtype=state.get("complaint_subtype"),
        #     severity=state.get("severity"),
        #     confidence=state.get("confidence"),
        #     description=state.get("analysis"),
        #     authority=state.get("authority"),
        #     status=state.get("status", "open"),
        #     resolved_image_path=state.get("resolved_image_path")
        # )
        return {"messages": [AIMessage(content=f"Stored in Vector DB -- {state['complaint_id']}")]}
    except Exception as e:
        print(f"Vector DB Error: {e}")
        return {"messages": [AIMessage(content=f"Vector DB failed: {str(e)}")]}


def tracker_node(state: ComplaintState):
    """Enhanced Analytics with proper category breakdown"""
    db = load_complaints_db()
    
    total = len(db)
    open_count = sum(1 for v in db.values() if v.get("status") == "open")
    closed_count = total - open_count

    type_count = defaultdict(int)
    subtype_count = defaultdict(int)
    authority_count = defaultdict(int)
    category_count = defaultdict(lambda: {"total": 0, "open": 0, "closed": 0})

    for v in db.values():
        ctype = v.get("type", "other").lower()
        csubtype = v.get("subtype", "other").lower()
        cauthority = v.get("authority", "Other")
        status = v.get("status", "open")

        type_count[ctype] += 1
        subtype_count[csubtype] += 1
        authority_count[cauthority] += 1

        # # Better category mapping
        # if cauthority == "Municipal Corporation":
        #     category = "Garbage & Sanitation"
        # elif cauthority == "MoRTH":
        #     category = "Road & Infrastructure"
        # elif cauthority == "BESCOM":
        #     category = "Street Light & Electricity"
        # else:
        #     category = "Other"

        category_count[cauthority]["total"] += 1
        if status == "open":
            category_count[cauthority]["open"] += 1
        else:
            category_count[cauthority]["closed"] += 1

    analytics = {
        "total_complaints": total,
        "open_complaints": open_count,
        "closed_complaints": closed_count,
        "by_complaint_type": dict(type_count),
        "by_complaint_subtype": dict(subtype_count),
        "by_category": {k: dict(v) for k, v in category_count.items()},
        "by_authority": dict(authority_count),
        "last_updated": datetime.now().isoformat()
    }

    # Pretty Console Output
    print(f"\n{'='*60}")
    print("COMPLAINT ANALYTICS")
    print(f"{'='*60}")
    print(f"Total Complaints      : {total}")
    print(f"Open Complaints       : {open_count}")
    print(f"Closed Complaints     : {closed_count}")

    print(f"\nBreakdown by Authority:")
    print("-" * 50)
    for auth, count in sorted(authority_count.items(), key=lambda x: x[1], reverse=True):
        print(f"{auth:<25} | Total: {count:>3}")

    print(f"\nBreakdown by Category:")
    print("-" * 50)
    for cat, data in category_count.items():
        print(f"{cat:<25} | Total: {data['total']:>3} | Open: {data['open']:>3} | Closed: {data['closed']:>3}")

    print(f"\nLast Updated: {analytics['last_updated']}")
    print(f"{'='*60}\n")

    return {"analytics": analytics, "messages": [AIMessage(content="Analytics generated for dashboard")]}


def closer_node(state: ComplaintState):
    complaint_id = state.get("complaint_id")
    if not complaint_id or complaint_id not in complaints_db:
        return {"messages": [AIMessage(content="Complaint ID not found")]}

    resolved_path = state.get("resolved_image_path")
    if resolved_path and os.path.exists(resolved_path):
        complaints_db[complaint_id]["resolved_image_path"] = resolved_path

    complaints_db[complaint_id]["status"] = "closed"
    complaints_db[complaint_id]["closed_at"] = datetime.now().isoformat()
    save_complaints_db(complaints_db)

    store_complaint_image(
        image_path=complaints_db[complaint_id]["image_path"],
        complaint_id=complaint_id,
        complaint_type=complaints_db[complaint_id]["type"],
        complaint_subtype=complaints_db[complaint_id]["subtype"],
        description="Resolved",
        authority=complaints_db[complaint_id]["authority"],
        status="closed",
        resolved_image_path=resolved_path
    )

    print(f"Complaint {complaint_id} CLOSED successfully")
    return {"status": "closed", "messages": [AIMessage(content=f"Complaint {complaint_id} closed successfully")]}


# ====================== BUILD GRAPH ======================
workflow = StateGraph(ComplaintState)

workflow.add_node("analyzer", analyzer_node)
workflow.add_node("router", router_node)
workflow.add_node("creator_bbmp", creator_bbmp)
workflow.add_node("creator_bwssb", creator_bwssb)
workflow.add_node("creator_bescom", creator_bescom)
workflow.add_node("creator_bda", creator_bda)
workflow.add_node("creator_bcp", creator_bcp)
workflow.add_node("creator_btp", creator_btp)
workflow.add_node("creator_kspcb", creator_kspcb)
workflow.add_node("creator_other", creator_other)
workflow.add_node("storage", storage_node)
workflow.add_node("tracker", tracker_node)

workflow.add_edge(START, "analyzer")
workflow.add_edge("analyzer", "router")

# Conditional Routing to Correct Department
def route_to_creator(state: ComplaintState):
    if state.get("complaint_type") == "duplicate":
        return "storage"
    auth = state.get("authority")
    if auth == "BBMP":
        return "creator_bbmp"
    elif auth == "BWSSB":
        return "creator_bwssb"
    elif auth == "BESCOM":
        return "creator_bescom"
    elif auth == "BDA":
        return "creator_bda"
    elif auth == "BCP":
        return "creator_bcp"
    elif auth == "BTP":
        return "creator_btp"
    elif auth == "KSPCB":
        return "creator_kspcb"
    else:
        return "creator_other"

workflow.add_conditional_edges(
    "router",
    route_to_creator,
    {
        "creator_bbmp": "creator_bbmp",
        "creator_bwssb": "creator_bwssb",
        "creator_bescom": "creator_bescom",
        "creator_bda": "creator_bda",
        "creator_bcp": "creator_bcp",
        "creator_btp": "creator_btp",
        "creator_kspcb": "creator_kspcb",
        "creator_other": "creator_other",
        "storage": "storage"
    }
)

workflow.add_edge("creator_bbmp", "storage")
workflow.add_edge("creator_bwssb", "storage")
workflow.add_edge("creator_bescom", "storage")
workflow.add_edge("creator_bda", "storage")
workflow.add_edge("creator_bcp", "storage")
workflow.add_edge("creator_btp", "storage")
workflow.add_edge("creator_kspcb", "storage")
workflow.add_edge("creator_other", "storage")
workflow.add_edge("storage", "tracker")
workflow.add_edge("tracker", END)

app = workflow.compile(checkpointer=memory)

#RAG Workflow
rag_workflow = StateGraph(ComplaintState)
rag_workflow.add_node("retrieval", retrieval_node)
rag_workflow.add_node("rag_llm", rag_llm_node)
rag_workflow.add_node("router", router_node)
rag_workflow.add_node("creator_bbmp", creator_bbmp)
rag_workflow.add_node("creator_bwssb", creator_bwssb)
rag_workflow.add_node("creator_bescom", creator_bescom)
rag_workflow.add_node("creator_bda", creator_bda)
rag_workflow.add_node("creator_bcp", creator_bcp)
rag_workflow.add_node("creator_btp", creator_btp)
rag_workflow.add_node("creator_kspcb", creator_kspcb)
rag_workflow.add_node("creator_other", creator_other)
rag_workflow.add_node("storage", storage_node)
rag_workflow.add_node("tracker", tracker_node)

rag_workflow.add_edge(START, "retrieval")
rag_workflow.add_edge("retrieval", "rag_llm")
rag_workflow.add_edge("rag_llm", "router")
rag_workflow.add_conditional_edges(
    "router",
    route_to_creator,
    {
        "creator_bbmp": "creator_bbmp",
        "creator_bwssb": "creator_bwssb",
        "creator_bescom": "creator_bescom",
        "creator_bda": "creator_bda",
        "creator_bcp": "creator_bcp",
        "creator_btp": "creator_btp",
        "creator_kspcb": "creator_kspcb",
        "creator_other": "creator_other",
        "storage": "storage"
    }
)

rag_workflow.add_edge("creator_bbmp", "storage")
rag_workflow.add_edge("creator_bwssb", "storage")
rag_workflow.add_edge("creator_bescom", "storage")
rag_workflow.add_edge("creator_bda", "storage")
rag_workflow.add_edge("creator_bcp", "storage")
rag_workflow.add_edge("creator_btp", "storage")
rag_workflow.add_edge("creator_kspcb", "storage")
rag_workflow.add_edge("creator_other", "storage")
rag_workflow.add_edge("storage", "tracker")
rag_workflow.add_edge("tracker", END)

rag_app = rag_workflow.compile(checkpointer=memory)

# Close Workflow
close_workflow = StateGraph(ComplaintState)
close_workflow.add_node("closer", closer_node)
close_workflow.add_edge(START, "closer")
close_workflow.add_edge("closer", END)
close_app = close_workflow.compile(checkpointer=memory)

# ====================== PROCESS FUNCTIONS ======================
def process_new_complaint(image_path: str, complaint_title: str = None, complaint_description: str = None):
    has_text_input = complaint_title or complaint_description

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
            display_name = complaint_title or complaint_description or "Text-based complaint"

    print(f"\n{'='*100}")
    print(f"Processing New Complaint: {display_name}")
    print(f"{'='*100}")

    inputs = {
        "image_path": image_path,
        "complaint_title": complaint_title,
        "complaint_description": complaint_description,
        "messages": [HumanMessage(content="Process new civil complaint")]
    }
    config = {"configurable": {"thread_id": f"thread_{uuid.uuid4().hex[:12]}"}}

    for chunk in app.stream(inputs, config, stream_mode="values"):
        if "messages" in chunk and chunk["messages"]:
            last_msg = chunk["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.content:
                print(f"-- {last_msg.content}")

    print(f"{'='*100}\n")

def process_new_complaint_rag(complaint_title: str, complaint_description: str, image_path: str = "", metadata_filter=None):
    """Process new complaint using RAG analysis"""
    display_name = complaint_title or complaint_description or "Text-based complaint"

    print(f"\n{'='*100}")
    print(f"Processing New Complaint with RAG: {display_name}")
    print(f"{'='*100}")

    inputs = {
        "image_path": image_path,
        "complaint_title": complaint_title,
        "complaint_description": complaint_description,
        "messages": [HumanMessage(content="Process new civil complaint with RAG analysis")]
    }
    config = {"configurable": {"thread_id": f"thread_{uuid.uuid4().hex[:12]}"}}

    for chunk in rag_app.stream(inputs, config, stream_mode="values"):
        if "messages" in chunk and chunk["messages"]:
            last_msg = chunk["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.content:
                print(f"-- {last_msg.content}")

    print(f"{'='*100}\n")

def close_complaint(complaint_id: str, resolved_image_path: str):
    if not os.path.exists(resolved_image_path):
        print(f"Resolved image not found: {resolved_image_path}")
        return

    inputs = {
        "complaint_id": complaint_id,
        "resolved_image_path": resolved_image_path,
        "messages": [HumanMessage(content="Close complaint")]
    }
    config = {"configurable": {"thread_id": f"close_{complaint_id}"}}

    for chunk in close_app.stream(inputs, config, stream_mode="values"):
        if "messages" in chunk and chunk["messages"]:
            last = chunk["messages"][-1]
            if isinstance(last, AIMessage):
                print(f"-- {last.content}")


# ====================== MAIN ======================
if __name__ == "__main__":
    print("Civil Complaint Resolver System Started\n")

    # Process all images in incoming folder
    for filename in os.listdir(INCOMING_FOLDER):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            process_new_complaint(os.path.join(INCOMING_FOLDER, filename))

    print("\n" + "="*80)
    print("Available Commands:")
    print("  new <image_path>           -- Process new complaint from image")
    print("  text <title>|<description> -- Process new complaint from text")
    print("  rag <title>|<description>  -- Process new complaint with RAG analysis")
    print("  close <ID> <resolved_path> -- Close a complaint")
    print("  analytics                  -- Show analytics")
    print("  list                       -- List all complaints")
    print("  exit                       -- Quit")
    print("="*80)

    while True:
        cmd = input("\nEnter command: ").strip()

        if cmd.lower() in ['exit', 'quit', 'q']:
            break
        elif cmd.startswith("new "):
            path = cmd[4:].strip()
            process_new_complaint(path)
        elif cmd.startswith("text"):
            text_input = cmd[4:].strip()
            if "|" in text_input:
                title, description = text_input.split("|", 1)
            else:
                title = text_input
            if text_input:
                title = text_input
            else:
                title = input("Title (optional): ").strip()

            if not description:
                description = read_multiline_description()
            if not title and not description:
                print("Please provide either a title or description.")
                continue

            description = description.strip() if description else ""
            process_new_complaint("", title, description)
        elif cmd.startswith("rag"):
            text_input = cmd[3:].strip()
            if "|" in text_input:
                title, description = text_input.split("|", 1)
            else:
                title = text_input
            if text_input:
                title = text_input
            else:
                title = input("Title (optional): ").strip()

            if not description:
                description = read_multiline_description()
            if not title and not description:
                print("Please provide either a title or description.")
                continue

            description = description.strip() if description else ""
            process_new_complaint_rag(title, description)
        elif cmd.startswith("close "):
            parts = cmd[6:].split()
            if len(parts) >= 2:
                close_complaint(parts[0], parts[1])
            else:
                print("Usage: close <ID> <resolved_image_path>")
        elif cmd == "analytics":
            tracker_node({"image_path": ""})
        elif cmd == "list":
            list_all_complaints()
        else:
            print("Unknown command. Try: new, text, close, analytics, list, exit")
