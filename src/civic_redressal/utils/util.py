import os
import requests
import base64
import re
import msvcrt
from PIL import Image
import imagehash
from io import BytesIO

from civic_redressal.db.json_db import load_complaints_db

def is_url(path: str | None) -> bool:
    if not path:
        return False
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

# def sanitize_text(text: str | None) -> str:
#     """Sanitize complaint title/description before sending to the model."""
#     if not text:
#         return ""
#     normalized = text.replace("\r\n", "\n").replace("\r", "\n")
#     # Keep printable characters, spaces, tabs, and newlines only.
#     normalized = "\n".join(
#         " ".join(ch for ch in line if ch.isprintable() or ch in "\t")
#         for line in normalized.splitlines()
#     )
#     # Trim and normalize whitespace on each line.
#     normalized = "\n".join(" ".join(line.split()) for line in normalized.splitlines())
#     return normalized.strip()

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