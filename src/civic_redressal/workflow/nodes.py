
# from datetime import datetime
# import json
# import os
# import uuid
# from langchain_core.messages import AIMessage, HumanMessage
# from collections import defaultdict

# from civic_redressal.config import PROMPT_FOLDER, PROMPT_NUMBER
# from civic_redressal.db.json_db import load_complaints_db, save_complaints_db
# from civic_redressal.retrieval.complaint_repository import store_complaint, store_complaint_image
# from civic_redressal.workflow.util import create_complaint
# from civic_redressal.workflow.state import ComplaintState
# from civic_redressal.utils.constants import CATEGORY_CIVIC_AGENCY_MAP, CATEGORY_PROMPT_OPTIONS, CIVIC_AGENCY_PROMPT_OPTIONS, SUBCATEGORY_PROMPT_OPTIONS
# from civic_redressal.utils.util import compute_image_hash, display_image, find_duplicate_image, format_context, image_to_base64, is_url, read_prompt, sanitize_text
# from civic_redressal.db.json_db import complaints_db

# def retrieval_node(state: ComplaintState, top_k=5, metadata_filter=None):
#     """
#     Retrieve similar complaints from Vector DB based on image and/or text
#     RAG pipeline: Retrieve similar complaints → Feed to Llama → Predict labels.
#     """

#     # 1. Retrieve top-k similar complaints
#     retrieved = retrieve_top_k_complaints(
#         title=state.get("complaint_title", "") or "",
#         description=state.get("complaint_description", "") or "",
#         top_k=top_k,
#         metadata_filter=metadata_filter
#     )

#     # print(f"Retrieval Node - Retrieved {len(retrieved)} complaints from vector DB for RAG context.")
#     # print(f"Top retrieved complaint (if any): {retrieved[0]['title'] if retrieved else 'None'}")
#     # print(f"Retrieval Node - Retrieved complaints: {[c['score'] for c in retrieved]}")
#     # print(f"Similarity scores of retrieved complaints: {[c['score'] for c in retrieved]}")

#     # 2. Format context
#     context = format_context(retrieved)

#     print(f"Retrieval Node - Found {len(retrieved)} similar complaints")
#     print("Retrieval Node - Similar complaints for RAG context:")
#     for i, complaint in enumerate(retrieved, 1):
#         print(f"  {i}. {complaint['title']} (Score: {complaint['score']})")
#     print(f"Retrieval Node - Formatted context for RAG:\n{context[:500]}...\n")

#     return {
#         "similar_complaints": context,
#         "messages": [AIMessage(content=f"Retrieved {len(retrieved)} similar complaints for reference.")]
#     }

# def rag_llm_node(state: ComplaintState):
#     """LLM node that takes retrieved complaints as context and predicts labels"""
#     from langchain_ollama import ChatOllama

#     similar_complaints = state.get("similar_complaints", "") or ""
#     complaint_title = sanitize_text(state.get("complaint_title"))
#     complaint_description = sanitize_text(state.get("complaint_description"))

#     print("similar_complaints content for RAG LLM Node:")
#     print(similar_complaints)
#     print("RAG LLM Node - Preparing prompt with retrieved complaints and input data...")

#     prompt = read_prompt(f"{PROMPT_FOLDER}/prompt_rag.txt")
#     prompt = prompt.replace("{CATEGORY_PROMPT_OPTIONS}", CATEGORY_PROMPT_OPTIONS)
#     prompt = prompt.replace("{SUBCATEGORY_PROMPT_OPTIONS}", SUBCATEGORY_PROMPT_OPTIONS)
#     prompt = prompt.replace("{CIVIC_AGENCY_PROMPT_OPTIONS}", CIVIC_AGENCY_PROMPT_OPTIONS)
#     prompt = prompt.replace("{similar_complaints}", similar_complaints)
#     prompt = prompt.replace("{complaint_title}", complaint_title)
#     prompt = prompt.replace("{complaint_description}", complaint_description)
    
#     print(f"RAG LLM Prompt:\n{prompt}\n")

#     try:
#         rag_llm = ChatOllama(model="llama3.2:3b", temperature=0.0)
#         message = HumanMessage(content=prompt)
#         result = rag_llm.invoke([message])
#         content = result.content.strip()
#         print(f"RAG LLM Output: {content[:200]}...")

#         result = json.loads(content)
#         print(f"RAG LLM Parsed Result - Type: {result.get('category')} | Subtype: {result.get('sub_category')} | Agency: {result.get('civic_agency')} | Severity: {result.get('severity')} | Confidence: {result.get('confidence')}")

#         complaint_id = f"COMP{str(uuid.uuid4())[:8].upper()}"

#         return {
#             "rag_analysis": content, 
#             "complaint_id": complaint_id,
#             "analysis": result.get("description", "Unknown issue"),
#             "complaint_type": result.get("category", "other"),
#             "complaint_subtype": result.get("sub_category", "other"),
#             "authority": result.get("civic_agency", "other"),
#             "severity": result.get("severity", "N/A"),
#             "confidence": result.get("confidence", 50),
#             # "image_hash": image_hash,
#             "complaint_title": complaint_title,
#             "complaint_description": complaint_description,
#             "messages": [AIMessage(content="RAG analysis complete.")]
#         }

#     except Exception as e:
#         print(f"RAG LLM error: {e}")
#         return {"rag_analysis": "", "messages": [AIMessage(content="RAG analysis failed, proceeding without it.")]}

# def analyzer_node(state: ComplaintState):
#     """Analyze image with improved prompt, optionally using textual inputs"""
#     from langchain_ollama import ChatOllama

#     image_path = state["image_path"]
#     complaint_title = sanitize_text(state.get("complaint_title"))
#     complaint_description = sanitize_text(state.get("complaint_description"))

#     # Check if we have textual inputs
#     has_text_input = bool(complaint_title or complaint_description)
#     # Check if we have an image input
#     has_image_input = bool(image_path and image_path.strip())

#     # Duplicate Check (only for images)
#     if has_image_input:
#         print("Checking for duplicate image using perceptual hashing...")
#         duplicate = find_duplicate_image(image_path)

#         if duplicate:
#             print(f"DUPLICATE IMAGE DETECTED! Similar to Complaint: {duplicate['complaint_id']}")
#             return {
#                 "complaint_id": None,
#                 "analysis": "Duplicate image detected",
#                 "complaint_type": "duplicate",
#                 "messages": [AIMessage(content=f"Duplicate image found (ID: {duplicate['complaint_id']}). Skipped.")]
#             }
    
#     text_content = ""
#     if has_text_input:
#         if complaint_title:
#             text_content += f"Title: {complaint_title}\n"
#         if complaint_description:
#             text_content += f"Description: {complaint_description}\n"

#     # Build analysis prompt based on available inputs
#     if has_text_input and not has_image_input:
#         # Text-based analysis
#         print("Analyzing complaint using provided text input...")

#         # Use text analysis model
#         try:
#             text_llm = ChatOllama(model="llama3.2:3b", temperature=0.0)

#             prompt = read_prompt(f"{PROMPT_FOLDER}/prompt{PROMPT_NUMBER}.txt")
#             prompt = prompt.replace("{CATEGORY_PROMPT_OPTIONS}", CATEGORY_PROMPT_OPTIONS)
#             prompt = prompt.replace("{SUBCATEGORY_PROMPT_OPTIONS}", SUBCATEGORY_PROMPT_OPTIONS)
#             prompt = prompt.replace("{CIVIC_AGENCY_PROMPT_OPTIONS}", CIVIC_AGENCY_PROMPT_OPTIONS)
#             prompt = prompt.replace("{text_content}", text_content.strip())

#             print(f"Text Analysis Prompt:\n{prompt}\n")

#             message = HumanMessage(content=prompt)
#             result = text_llm.invoke([message])
#             content = result.content.strip()

#         except Exception as e:
#             print(f"Text analysis model not available ({e}), using fallback")
#             # Fallback analysis based on keywords
#             text_combined = (complaint_title or "") + " " + (complaint_description or "")
#             text_lower = text_combined.lower()

#             if any(word in text_lower for word in ["garbage", "waste", "trash", "rubbish"]):
#                 analysis = {"description": complaint_description or complaint_title or "Garbage issue", "category": "Garbage and Unsanitary Practices", "sub_category": "other", "confidence": 70, "severity": "medium"}
#             elif any(word in text_lower for word in ["road", "pothole", "crack", "damage", "hole"]):
#                 analysis = {"description": complaint_description or complaint_title or "Road damage issue", "category": "Mobility - Roads, Footpaths and Infrastructure", "sub_category": "pothole", "confidence": 70, "severity": "high"}
#             elif any(word in text_lower for word in ["light", "streetlight", "lamp", "electricity", "power"]):
#                 analysis = {"description": complaint_description or complaint_title or "Street light issue", "category": "Streetlights", "sub_category": "not working", "confidence": 70, "severity": "medium"}
#             else:
#                 analysis = {"description": complaint_description or complaint_title or "General civic issue", "category": "other", "sub_category": "other", "confidence": 50, "severity": "low"}

#     else:
#         # Image-based analysis (existing logic)
#         print("Analyzing complaint using image...")
#         try:
#             vision_llm = ChatOllama(model="gemma4:e4b", temperature=0.0)
#             base64_img = image_to_base64(image_path)

#             prompt = f"""You are an expert civic complaint analyzer for Bengaluru city.
# Analyze the image and return ONLY valid JSON with these exact keys:
# {{
#   "description": "Clear one-sentence description of the issue",
#   "complaint_type": "{CATEGORY_PROMPT_OPTIONS}",
#   "complaint_subtype": "{SUBCATEGORY_PROMPT_OPTIONS}",
#   "authority": "{CIVIC_AGENCY_PROMPT_OPTIONS}",
#   "confidence": complaint_type complaint_subtype and authority prediction confidence in the range 0 to 100,
#   "severity": "low | medium | high"
# }}
# Use only these complaint_type values from the list above.
# Do not add any extra text or explanation.

# Complaint Text:
# {text_content}"""

#             message = HumanMessage(
#                 content=[
#                     {"type": "text", "text": prompt},
#                     {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
#                 ]
#             )

#             result = vision_llm.invoke([message])
#             content = result.content.strip()
#             print(f"Vision Model Raw Output: {content[:200]}...")

#         except Exception as e:
#             print(f"Vision model not available ({e}), using basic image analysis")
#             # Fallback for image analysis
#             filename = os.path.basename(image_path).lower() if not is_url(image_path) else "image"
#             if "garbage" in filename or "waste" in filename:
#                 analysis = {"description": "Garbage issue detected from image", "category": "Garbage and Unsanitary Practices", "sub_category": "other", "confidence": 60, "severity": "medium"}
#             elif "road" in filename or "pothole" in filename:
#                 analysis = {"description": "Road damage detected from image", "category": "Mobility - Roads, Footpaths and Infrastructure", "sub_category": "pothole", "confidence": 60, "severity": "high"}
#             elif "light" in filename or "street" in filename:
#                 analysis = {"description": "Street light issue detected from image", "category": "Streetlights", "sub_category": "not working", "confidence": 60, "severity": "medium"}
#             else:
#                 analysis = {"description": "General civic issue detected from image", "category": "other", "sub_category": "other", "confidence": 50, "severity": "low"}

#     # Parse the analysis result
#     if 'analysis' not in locals():
#         try:
#             # Strip markdown code blocks if present (```json ... ```)
#             if content.startswith("```"):
#                 content = content.lstrip("`").lstrip("json").lstrip("JSON").strip()
#                 if content.endswith("```"):
#                     content = content[:-3].strip()

#             analysis = json.loads(content)
#             print(f"Model returned - Analysis: {analysis.get('description')} | Type: {analysis.get('category')} | Subtype: {analysis.get('sub_category')} | Authority: {analysis.get('civic_agency')} | Severity: {analysis.get('severity')} | Confidence: {analysis.get('confidence')}")
#         except Exception as parse_error:
#             print(f"Failed to parse JSON: {parse_error}")
#             analysis = {"description": content[:300], "category": "other", "sub_category": "other", "confidence": 50, "severity": "low"}

#     complaint_id = f"COMP{str(uuid.uuid4())[:8].upper()}"
#     image_hash = compute_image_hash(image_path) if not has_text_input else ""

#     print(f"New Complaint ID Generated: {complaint_id}")
#     if not has_text_input:
#         display_image(image_path)

#     return {
#         "complaint_id": complaint_id,
#         "analysis": analysis.get("description", "Unknown issue"),
#         "complaint_type": analysis.get("category", "other"),
#         "complaint_subtype": analysis.get("sub_category", "other"),
#         "authority": analysis.get("civic_agency", "other"),
#         "severity": analysis.get("severity", "N/A"),
#         "confidence": analysis.get("confidence", 50),
#         "image_hash": image_hash,
#         "complaint_title": complaint_title,
#         "complaint_description": complaint_description,
#         "messages": [AIMessage(content=f"Analysis complete. Type: {analysis.get('category')} | ID: {complaint_id}")]
#     }


# def router_node(state: ComplaintState):
#     """Improved routing logic"""
#     if state.get("complaint_type") == "duplicate":
#         return {"authority": None, "messages": [AIMessage(content="Duplicate - No routing")]}

#     ctype = str(state.get("complaint_type", "")).strip()

#     print(f"Routing based on complaint type: '{ctype}'")

#     if ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BBMP", []):
#         actual_authority = "BBMP"
#     elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BESCOM", []):
#         actual_authority = "BESCOM"
#     elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BWSSB", []):
#         actual_authority = "BWSSB"
#     elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BCP", []):
#         actual_authority = "BCP"
#     elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BTP", []):
#         actual_authority = "BTP"
#     elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("KSPCB", []):
#         actual_authority = "KSPCB"
#     elif ctype in CATEGORY_CIVIC_AGENCY_MAP.get("BDA", []):
#         actual_authority = "BDA"
#     else:
#         actual_authority = "Other"

#     model_authority = state.get("authority", "other")
#     if model_authority and model_authority != actual_authority:
#         print(f"⚠️ Model predicted authority '{model_authority}' does not match routing logic '{actual_authority}' for category '{ctype}'. Using routing logic authority.")
#     else:
#         print(f"Model predicted authority '{model_authority}' matches routing logic '{actual_authority}' for category '{ctype}'.")
    

#     print(f"Routing Decision: '{ctype}' → {actual_authority}")

#     return {
#         "authority": actual_authority,
#         "messages": [AIMessage(content=f"Routed to -- {actual_authority} (Category: {ctype})")]
#     }

# def creator_bbmp(state: ComplaintState):
#     return create_complaint(state, "BBMP")

# def creator_bescom(state: ComplaintState):
#     return create_complaint(state, "BESCOM")

# def creator_bwssb(state: ComplaintState):
#     return create_complaint(state, "BWSSB")

# def creator_kspcb(state: ComplaintState):
#     return create_complaint(state, "KSPCB")

# def creator_bcp(state: ComplaintState):
#     return create_complaint(state, "BCP")

# def creator_btp(state: ComplaintState):
#     return create_complaint(state, "BTP")

# def creator_bda(state: ComplaintState):
#     return create_complaint(state, "BDA")

# def creator_other(state: ComplaintState):
#     return create_complaint(state, "Other")


# def storage_node(state: ComplaintState):
#     if not state.get("complaint_id"):
#         return {"messages": [AIMessage(content="Skipped storage due to duplicate")]}
#     try:
#         print(f"Storing complaint: {state['complaint_id']}")
#         print(f"Description: {state.get('complaint_description')}")
#         print(f"Analysis: {state.get('analysis')}")
#         docid = store_complaint(
#             complaint_id=state["complaint_id"],
#             title=state.get("complaint_title"),
#             description=state.get("complaint_description"),
#             category=state.get("complaint_type"),
#             sub_category=state.get("complaint_subtype"),
#             analysis=state.get("analysis"),
#             civic_agency=state.get("authority"),
#             status=state.get("status", "open"),
#             severity=state.get("severity"),
#             confidence=state.get("confidence"),
#             image_path=state["image_path"],
#             image_hash=state.get("image_hash", "")
#         )
#         print(f"Complaint stored in Vector DB with docid: {docid}")
#         # store_complaint_image(
#         #     image_path=state["image_path"],
#         #     complaint_id=state["complaint_id"],
#         #     complaint_title=state.get("complaint_title"),
#         #     complaint_description=state.get("complaint_description"),
#         #     complaint_type=state.get("complaint_type"),
#         #     complaint_subtype=state.get("complaint_subtype"),
#         #     severity=state.get("severity"),
#         #     confidence=state.get("confidence"),
#         #     description=state.get("analysis"),
#         #     authority=state.get("authority"),
#         #     status=state.get("status", "open"),
#         #     resolved_image_path=state.get("resolved_image_path")
#         # )
#         return {"messages": [AIMessage(content=f"Stored in Vector DB -- {state['complaint_id']}")]}
#     except Exception as e:
#         print(f"Vector DB Error: {e}")
#         return {"messages": [AIMessage(content=f"Vector DB failed: {str(e)}")]}


# def tracker_node(state: ComplaintState):
#     """Enhanced Analytics with proper category breakdown"""
#     db = load_complaints_db()
    
#     total = len(db)
#     open_count = sum(1 for v in db.values() if v.get("status") == "open")
#     closed_count = total - open_count

#     type_count = defaultdict(int)
#     subtype_count = defaultdict(int)
#     authority_count = defaultdict(int)
#     category_count = defaultdict(lambda: {"total": 0, "open": 0, "closed": 0})

#     for v in db.values():
#         ctype = v.get("type", "other").lower()
#         csubtype = v.get("subtype", "other").lower()
#         cauthority = v.get("authority", "Other")
#         status = v.get("status", "open")

#         type_count[ctype] += 1
#         subtype_count[csubtype] += 1
#         authority_count[cauthority] += 1

#         # # Better category mapping
#         # if cauthority == "Municipal Corporation":
#         #     category = "Garbage & Sanitation"
#         # elif cauthority == "MoRTH":
#         #     category = "Road & Infrastructure"
#         # elif cauthority == "BESCOM":
#         #     category = "Street Light & Electricity"
#         # else:
#         #     category = "Other"

#         category_count[cauthority]["total"] += 1
#         if status == "open":
#             category_count[cauthority]["open"] += 1
#         else:
#             category_count[cauthority]["closed"] += 1

#     analytics = {
#         "total_complaints": total,
#         "open_complaints": open_count,
#         "closed_complaints": closed_count,
#         "by_complaint_type": dict(type_count),
#         "by_complaint_subtype": dict(subtype_count),
#         "by_category": {k: dict(v) for k, v in category_count.items()},
#         "by_authority": dict(authority_count),
#         "last_updated": datetime.now().isoformat()
#     }

#     # Pretty Console Output
#     print(f"\n{'='*60}")
#     print("COMPLAINT ANALYTICS")
#     print(f"{'='*60}")
#     print(f"Total Complaints      : {total}")
#     print(f"Open Complaints       : {open_count}")
#     print(f"Closed Complaints     : {closed_count}")

#     print(f"\nBreakdown by Authority:")
#     print("-" * 50)
#     for auth, count in sorted(authority_count.items(), key=lambda x: x[1], reverse=True):
#         print(f"{auth:<25} | Total: {count:>3}")

#     print(f"\nBreakdown by Category:")
#     print("-" * 50)
#     for cat, data in category_count.items():
#         print(f"{cat:<25} | Total: {data['total']:>3} | Open: {data['open']:>3} | Closed: {data['closed']:>3}")

#     print(f"\nLast Updated: {analytics['last_updated']}")
#     print(f"{'='*60}\n")

#     return {"analytics": analytics, "messages": [AIMessage(content="Analytics generated for dashboard")]}


# def closer_node(state: ComplaintState):
#     complaint_id = state.get("complaint_id")
#     if not complaint_id or complaint_id not in complaints_db:
#         return {"messages": [AIMessage(content="Complaint ID not found")]}

#     resolved_path = state.get("resolved_image_path")
#     if resolved_path and os.path.exists(resolved_path):
#         complaints_db[complaint_id]["resolved_image_path"] = resolved_path

#     complaints_db[complaint_id]["status"] = "closed"
#     complaints_db[complaint_id]["closed_at"] = datetime.now().isoformat()
#     save_complaints_db(complaints_db)

#     store_complaint_image(
#         image_path=complaints_db[complaint_id]["image_path"],
#         complaint_id=complaint_id,
#         complaint_type=complaints_db[complaint_id]["type"],
#         complaint_subtype=complaints_db[complaint_id]["subtype"],
#         description="Resolved",
#         authority=complaints_db[complaint_id]["authority"],
#         status="closed",
#         resolved_image_path=resolved_path
#     )

#     print(f"Complaint {complaint_id} CLOSED successfully")
#     return {"status": "closed", "messages": [AIMessage(content=f"Complaint {complaint_id} closed successfully")]}
