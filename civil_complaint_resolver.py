# ========================================================
# CIVIL COMPLAINT RESOLVER - FIXED VERSION (with Proper Routing)
# ========================================================

import os
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
from complaint_vector_db import store_complaint_image, search_complaints, list_all_complaints

print("=== Civil Complaint Resolver - Fixed Routing + Better Analytics ===\n")

# ========================= CONFIG =========================
INCOMING_FOLDER = "./incoming_complaints"
RESOLVED_FOLDER = "./resolved_complaints"
SENT_MESSAGES_FOLDER = "./sent_messages"
COMPLAINTS_DB_FILE = "complaints_db.json"

# Create folders
os.makedirs(INCOMING_FOLDER, exist_ok=True)
os.makedirs(RESOLVED_FOLDER, exist_ok=True)
os.makedirs(SENT_MESSAGES_FOLDER, exist_ok=True)

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

def sanitize_text(text: str | None) -> str:
    """Sanitize complaint title/description before sending to the model."""
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # Keep printable characters, spaces, tabs, and newlines only.
    normalized = "\n".join(
        " ".join(ch for ch in line if ch.isprintable() or ch in "\t")
        for line in normalized.splitlines()
    )
    # Trim and normalize whitespace on each line.
    normalized = "\n".join(" ".join(line.split()) for line in normalized.splitlines())
    return normalized.strip()


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

# ====================== NODES ======================

def analyzer_node(state: ComplaintState):
    """Analyze image with improved prompt, optionally using textual inputs"""
    from langchain_ollama import ChatOllama

    image_path = state["image_path"]
    complaint_title = sanitize_text(state.get("complaint_title"))
    complaint_description = sanitize_text(state.get("complaint_description"))

    # Check if we have textual inputs
    has_text_input = bool(complaint_title or complaint_description)

    # Duplicate Check (only for images)
    if not has_text_input:
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

    # Build analysis prompt based on available inputs
    if has_text_input:
        # Text-based analysis
        print("Analyzing complaint using provided text input...")
        text_content = ""
        if complaint_title:
            text_content += f"Title: {complaint_title}\n"
        if complaint_description:
            text_content += f"Description: {complaint_description}\n"

        # Use text analysis model
        try:
            text_llm = ChatOllama(model="llama3.2:3b", temperature=0.0)

            prompt = f"""You are an expert civic complaint analyzer for Bengaluru city.
Analyze the following complaint text and return ONLY valid JSON with these exact keys:
{{
  "description": "Clear one-sentence description of the issue",
  "complaint_type": "garbage | road_damage | street_light | other",
  "complaint_subtype": "More specific subtype if possible (organic | plastic | paper | glass | metal | other) for garbage,
    (pothole | crack | manhole | other) for road damage, (not working | flickering | other) for street light",
  "confidence": complaint type and subtype prediction confidence in the range 0 to 100,
  "severity": "low | medium | high"
}}
Use only these complaint_type values: garbage, road_damage, street_light, or other.
Do not add any extra text or explanation.

Complaint Text:
{text_content}"""

            message = HumanMessage(content=prompt)
            result = text_llm.invoke([message])
            content = result.content.strip()

        except Exception as e:
            print(f"Text analysis model not available ({e}), using fallback")
            # Fallback analysis based on keywords
            text_combined = (complaint_title or "") + " " + (complaint_description or "")
            text_lower = text_combined.lower()

            if any(word in text_lower for word in ["garbage", "waste", "trash", "rubbish"]):
                analysis = {"description": complaint_description or complaint_title or "Garbage issue", "complaint_type": "garbage", "complaint_subtype": "other", "confidence": 70, "severity": "medium"}
            elif any(word in text_lower for word in ["road", "pothole", "crack", "damage", "hole"]):
                analysis = {"description": complaint_description or complaint_title or "Road damage issue", "complaint_type": "road_damage", "complaint_subtype": "pothole", "confidence": 70, "severity": "high"}
            elif any(word in text_lower for word in ["light", "streetlight", "lamp", "electricity", "power"]):
                analysis = {"description": complaint_description or complaint_title or "Street light issue", "complaint_type": "street_light", "complaint_subtype": "not working", "confidence": 70, "severity": "medium"}
            else:
                analysis = {"description": complaint_description or complaint_title or "General civic issue", "complaint_type": "other", "complaint_subtype": "other", "confidence": 50, "severity": "low"}

    else:
        # Image-based analysis (existing logic)
        print("Analyzing complaint using image...")
        try:
            vision_llm = ChatOllama(model="gemma4:e4b", temperature=0.0)
            base64_img = image_to_base64(image_path)

            prompt = """You are an expert civic complaint analyzer for Bengaluru city.
Analyze the image and return ONLY valid JSON with these exact keys:
{
  "description": "Clear one-sentence description of the issue",
  "complaint_type": "garbage | road_damage | street_light | other",
  "complaint_subtype": "More specific subtype if possible (organic | plastic | paper | glass | metal | other) for garbage,
    (pothole | crack | manhole | other) for road damage, (not working | flickering | other) for street light",
  "confidence": complaint type and subtype prediction confidence in the range 0 to 100,
  "severity": "low | medium | high"
}
Use only these complaint_type values: garbage, road_damage, street_light, or other.
Do not add any extra text or explanation."""

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
                analysis = {"description": "Garbage issue detected from image", "complaint_type": "garbage", "complaint_subtype": "other", "confidence": 60, "severity": "medium"}
            elif "road" in filename or "pothole" in filename:
                analysis = {"description": "Road damage detected from image", "complaint_type": "road_damage", "complaint_subtype": "pothole", "confidence": 60, "severity": "high"}
            elif "light" in filename or "street" in filename:
                analysis = {"description": "Street light issue detected from image", "complaint_type": "street_light", "complaint_subtype": "not working", "confidence": 60, "severity": "medium"}
            else:
                analysis = {"description": "General civic issue detected from image", "complaint_type": "other", "complaint_subtype": "other", "confidence": 50, "severity": "low"}

    # Parse the analysis result
    if 'analysis' not in locals():
        try:
            # Strip markdown code blocks if present (```json ... ```)
            if content.startswith("```"):
                content = content.lstrip("`").lstrip("json").lstrip("JSON").strip()
                if content.endswith("```"):
                    content = content[:-3].strip()

            analysis = json.loads(content)
            print(f"Model returned - Type: {analysis.get('complaint_type')} | Subtype: {analysis.get('complaint_subtype')} | Severity: {analysis.get('severity')} | Confidence: {analysis.get('confidence')}")
        except Exception as parse_error:
            print(f"Failed to parse JSON: {parse_error}")
            analysis = {"description": content[:300], "complaint_type": "other", "complaint_subtype": "other", "confidence": 50, "severity": "low"}

    complaint_id = f"COMP{str(uuid.uuid4())[:8].upper()}"
    image_hash = compute_image_hash(image_path) if not has_text_input else ""

    print(f"New Complaint ID Generated: {complaint_id}")
    if not has_text_input:
        display_image(image_path)

    return {
        "complaint_id": complaint_id,
        "analysis": analysis.get("description", "Unknown issue"),
        "complaint_type": analysis.get("complaint_type", "other"),
        "complaint_subtype": analysis.get("complaint_subtype", "other"),
        "severity": analysis.get("severity", "N/A"),
        "confidence": analysis.get("confidence", 50),
        "image_hash": image_hash,
        "messages": [AIMessage(content=f"Analysis complete. Type: {analysis.get('complaint_type')} | ID: {complaint_id}")]
    }


def router_node(state: ComplaintState):
    """Improved routing logic"""
    if state.get("complaint_type") == "duplicate":
        return {"authority": None, "messages": [AIMessage(content="Duplicate - No routing")]}

    ctype = str(state.get("complaint_type", "")).lower().strip()

    if ctype in ["garbage", "waste"] or "garbage" in ctype or "waste" in ctype:
        authority = "Municipal Corporation"
    elif ctype in ["road_damage", "pothole", "road"] or "road" in ctype or "pothole" in ctype:
        authority = "MoRTH"
    elif ctype in ["street_light", "light", "lamppost", "electricity"] or "light" in ctype or "electric" in ctype:
        authority = "BESCOM"
    else:
        authority = "Other"

    print(f"Routing Decision: '{ctype}' → {authority}")

    return {
        "authority": authority,
        "messages": [AIMessage(content=f"Routed to -- {authority} (Type: {ctype})")]
    }


def create_complaint(state: ComplaintState, authority: str):
    """Common function to create complaint for any department"""
    if not state.get("complaint_id"):
        return {"messages": [AIMessage(content="Registration skipped due to duplicate")]}

    complaint_id = state["complaint_id"]

    message_text = f"""NEW CIVIL COMPLAINT
Complaint ID     : {complaint_id}
Type             : {state.get('complaint_type', 'N/A')}
Description      : {state.get('analysis', 'N/A')}
Authority        : {authority}
Submitted Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Image Location   : {state['image_path']}

Please take necessary action at the earliest.
"""

    msg_path = f"{SENT_MESSAGES_FOLDER}/{complaint_id}.txt"
    with open(msg_path, "w", encoding="utf-8") as f:
        f.write(message_text)

    complaints_db[complaint_id] = {
        "type": state.get("complaint_type"),
        "subtype": state.get("complaint_subtype"),
        "description": state.get("analysis"),
        "severity": state.get("severity"),
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


def creator_municipal(state: ComplaintState):
    return create_complaint(state, "Municipal Corporation")

def creator_morth(state: ComplaintState):
    return create_complaint(state, "MoRTH")

def creator_bescom(state: ComplaintState):
    return create_complaint(state, "BESCOM")

def creator_other(state: ComplaintState):
    return create_complaint(state, "Other")


def storage_node(state: ComplaintState):
    if not state.get("complaint_id"):
        return {"messages": [AIMessage(content="Skipped storage due to duplicate")]}
    try:
        store_complaint_image(
            image_path=state["image_path"],
            complaint_id=state["complaint_id"],
            complaint_type=state.get("complaint_type"),
            complaint_subtype=state.get("complaint_subtype"),
            severity=state.get("severity"),
            confidence=state.get("confidence"),
            description=state.get("analysis"),
            authority=state.get("authority"),
            status=state.get("status", "open"),
            resolved_image_path=state.get("resolved_image_path")
        )
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

    authority_count = defaultdict(int)
    category_count = defaultdict(lambda: {"total": 0, "open": 0, "closed": 0})
    type_count = defaultdict(int)
    subtype_count = defaultdict(int)

    for v in db.values():
        ctype = v.get("type", "other").lower()
        csubtype = v.get("subtype", "other").lower()
        authority = v.get("authority", "Other")
        status = v.get("status", "open")

        type_count[ctype] += 1
        authority_count[authority] += 1

        # Better category mapping
        if authority == "Municipal Corporation":
            category = "Garbage & Sanitation"
        elif authority == "MoRTH":
            category = "Road & Infrastructure"
        elif authority == "BESCOM":
            category = "Street Light & Electricity"
        else:
            category = "Other"

        category_count[category]["total"] += 1
        if status == "open":
            category_count[category]["open"] += 1
        else:
            category_count[category]["closed"] += 1

    analytics = {
        "total_complaints": total,
        "open_complaints": open_count,
        "closed_complaints": closed_count,
        "by_complaint_type": dict(type_count),
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
workflow.add_node("creator_municipal", creator_municipal)
workflow.add_node("creator_morth", creator_morth)
workflow.add_node("creator_bescom", creator_bescom)
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
    if auth == "Municipal Corporation":
        return "creator_municipal"
    elif auth == "MoRTH":
        return "creator_morth"
    elif auth == "BESCOM":
        return "creator_bescom"
    else:
        return "creator_other"

workflow.add_conditional_edges(
    "router",
    route_to_creator,
    {
        "creator_municipal": "creator_municipal",
        "creator_morth": "creator_morth",
        "creator_bescom": "creator_bescom",
        "creator_other": "creator_other",
        "storage": "storage"
    }
)

workflow.add_edge("creator_municipal", "storage")
workflow.add_edge("creator_morth", "storage")
workflow.add_edge("creator_bescom", "storage")
workflow.add_edge("creator_other", "storage")
workflow.add_edge("storage", "tracker")
workflow.add_edge("tracker", END)

app = workflow.compile(checkpointer=memory)

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
    print("  close <ID> <resolved_path> -- Close a complaint")
    print("  analytics                  -- Show analytics")
    print("  list                       -- List all complaints")
    print("  exit                       -- Quit")
    print("="*80)

    while True:
        cmd = input("\nEnter command: ").strip()

        if cmd.lower() in ['exit', 'quit']:
            break
        elif cmd.startswith("new "):
            path = cmd[4:].strip()
            process_new_complaint(path)
        elif cmd.startswith("text"):
            text_input = cmd[4:].strip()
            if text_input:
                title = sanitize_text(text_input)
            else:
                title = sanitize_text(input("Title (optional): ").strip())

            description = read_multiline_description()
            if not title and not description:
                print("Please provide either a title or description.")
                continue

            description = sanitize_text(description)
            process_new_complaint("", title, description)
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