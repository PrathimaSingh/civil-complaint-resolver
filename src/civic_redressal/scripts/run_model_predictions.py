#!/usr/bin/env python3
"""
Batch prediction utility: runs the complaint resolver model on all rows from model_pe_test.csv
and saves predictions to results/model_predictions.csv
"""

import os
import csv
import json
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

# ========================= CONFIG =========================
PROMPT_NUMBER=0
TEST_CSV_PATH = "data/model_pe_test.csv"
OUTPUT_CSV_PATH = "results/model_predictions{PROMPT_NUMBER}.csv"
PROMPT_FOLDER = "prompts"

# Category choices (from civil_complaint_resolver.py)
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

def read_prompt(prompt_path):
    with open(prompt_path, 'r') as file:
        return file.read().strip()

def sanitize_text(text: str | None) -> str:
    """Sanitize text before sending to the model."""
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(
        " ".join(ch for ch in line if ch.isprintable() or ch in "\t")
        for line in normalized.splitlines()
    )
    normalized = "\n".join(" ".join(line.split()) for line in normalized.splitlines())
    return normalized.strip()


def predict_complaint(title: str, description: str) -> dict:
    """
    Run the text-based analyzer on complaint title and description.
    Returns a dict with predicted: description, category, sub_category, civic_agency, confidence, severity
    """

    # Path to the prompt file
    prompt_path = f"./{PROMPT_FOLDER}/prompt1.txt"
    # title = sanitize_text(title)
    # description = sanitize_text(description)
    
    text_content = ""
    if title:
        text_content += f"Title: {title}\n"
    if description:
        text_content += f"Description: {description}\n"

    try:
        text_llm = ChatOllama(model="llama3.2:3b", temperature=0.0)
        prompt = read_prompt(prompt_path)
        prompt = prompt.replace("{CATEGORY_PROMPT_OPTIONS}", CATEGORY_PROMPT_OPTIONS)
        prompt = prompt.replace("{SUBCATEGORY_PROMPT_OPTIONS}", SUBCATEGORY_PROMPT_OPTIONS)
        prompt = prompt.replace("{CIVIC_AGENCY_PROMPT_OPTIONS}", CIVIC_AGENCY_PROMPT_OPTIONS)
        prompt = prompt.replace("{text_content}", text_content.strip())
#         prompt = f"""You are an expert civic complaint analyzer for Bengaluru city.
# Analyze the following complaint text and return ONLY valid JSON with these exact keys:
# {{
#   "description": "Clear one-sentence description of the issue",
#   "category": "{CATEGORY_PROMPT_OPTIONS} | other",
#   "sub_category": "{SUBCATEGORY_PROMPT_OPTIONS}",
#   "civic_agency": "{CIVIC_AGENCY_PROMPT_OPTIONS}",
#   "confidence": "integer from 0 to 100 representing prediction confidence of category, sub_category and civic_agency",
#   "severity": "low | medium | high"
# }}
# Use only these category values from the list above.
# Do not add any extra text or explanation.

# Complaint Text:
# {text_content}"""

        # print(f"PROMPT:\n{prompt}\n")
        message = HumanMessage(content=prompt)
        result = text_llm.invoke([message])
        content = result.content.strip()
        
        # Strip markdown code blocks if present
        if content.startswith("```"):
            content = content.lstrip("`").lstrip("json").lstrip("JSON").strip()
            if content.endswith("```"):
                content = content[:-3].strip()
        
        analysis = json.loads(content)
        return {
            "description": analysis.get("description", ""),
            "category": analysis.get("category", "other"),
            "sub_category": analysis.get("sub_category", "other"),
            "civic_agency": analysis.get("civic_agency"),
            "confidence": analysis.get("confidence", 50),
            "severity": analysis.get("severity", "N/A"),
            "error": None
        }
    except Exception as e:
        print(f"Error during prediction: {e}")
        # Fallback: keyword-based prediction
        text_combined = (title or "") + " " + (description or "")
        text_lower = text_combined.lower()

        if any(word in text_lower for word in ["garbage", "waste", "trash", "rubbish"]):
            return {
                "description": description or title or "Garbage issue",
                "category": "Garbage and Unsanitary Practices",
                "sub_category": "other",
                "civic_agency": "BBMP",
                "confidence": 60,
                "severity": "medium",
                "error": str(e)
            }
        elif any(word in text_lower for word in ["road", "pothole", "crack", "damage"]):
            return {
                "description": description or title or "Road damage issue",
                "category": "Mobility - Roads, Footpaths and Infrastructure",
                "sub_category": "pothole",
                "civic_agency": "BDA",
                "confidence": 60,
                "severity": "high",
                "error": str(e)
            }
        elif any(word in text_lower for word in ["light", "streetlight", "lamp"]):
            return {
                "description": description or title or "Streetlight issue",
                "category": "Streetlights",
                "sub_category": "not working",
                "civic_agency": "BESCOM",
                "confidence": 60,
                "severity": "medium",
                "error": str(e)
            }
        else:
            return {
                "description": description or title or "General civic issue",
                "category": "other",
                "sub_category": "other",
                "civic_agency": "other",
                "confidence": 50,
                "severity": "low",
                "error": str(e)
            }


def run_batch_predictions():
    """Read test CSV and run predictions for all rows."""
    if not os.path.exists(TEST_CSV_PATH):
        print(f"Error: {TEST_CSV_PATH} not found")
        return

    # Ensure results directory exists
    os.makedirs(os.path.dirname(OUTPUT_CSV_PATH), exist_ok=True)

    results = []
    total_rows = 0
    
    print(f"Reading {TEST_CSV_PATH}...")
    with open(TEST_CSV_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, 1):
            # if idx > 5:  # Limit to first 5 rows for testing
            #     break
            total_rows += 1
            title = row.get("title", "").strip()
            description = row.get("description", "").strip()
            
            print(f"[{idx}] Processing: {title[:50]}..." if title else f"[{idx}] Processing description...")
            
            prediction = predict_complaint(title, description)

            # print(f"   Predicted Category: {prediction['category']} Subcategory: {prediction['sub_category']}, Civic Agency: {prediction['civic_agency']}, Confidence: {prediction['confidence']}%, Severity: {prediction['severity']}")
            
            # Combine input + prediction
            result_row = {
                "row_id": idx,
                "created_at": row.get("created_at"),
                "ward_id": row.get("ward_id"),
                "title": title,
                "description": description[:100] if description else "",  # Truncate for CSV readability
                "location": row.get("location"),
                "address": row.get("address"),
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
                "ward_title": row.get("ward_title"),
                "predicted_category": prediction["category"],
                "predicted_sub_category": prediction["sub_category"],
                "predicted_civic_agency": prediction["civic_agency"],
                "predicted_description": prediction["description"],
                "predicted_confidence": prediction["confidence"],
                "predicted_severity": prediction["severity"],
                "error": prediction["error"] or ""
            }
            results.append(result_row)

    # Write results to CSV
    print(f"\nWriting {len(results)} predictions to {OUTPUT_CSV_PATH}...")
    if results:
        fieldnames = results[0].keys()
        with open(OUTPUT_CSV_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"✅ Batch predictions completed!")
        print(f"   Total rows processed: {total_rows}")
        print(f"   Results saved to: {OUTPUT_CSV_PATH}")
    else:
        print("No data to process")


if __name__ == "__main__":
    print("="*80)
    print("BATCH COMPLAINT PREDICTION UTILITY")
    print("="*80)
    print("Enter the prompt number:")
    PROMPT_NUMBER = input().strip()
    OUTPUT_CSV_PATH = f"results/model_predictions_{PROMPT_NUMBER}.csv"
    run_batch_predictions()
