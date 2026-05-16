RETRIEVAL_RAG_PROMPT = """
You are an expert civic complaint classification expert for Bengaluru city.

NEW COMPLAINT TO CLASSIFY:
Title: {title}
Description: {description}

SIMILAR PAST COMPLAINTS (for reference):
{similar_complaints}

TASK: Predict the correct labels for the NEW complaint above.

Respond ONLY with valid JSON:
{
  "description": "A clear one-sentence summary of the issue.",
  "category": "One value from {{CATEGORY_PROMPT_OPTIONS}}",
  "sub_category": "One value from {{SUBCATEGORY_PROMPT_OPTIONS}}",
  "civic_agency": "One value from {{CIVIC_AGENCY_PROMPT_OPTIONS}}",
  "confidence": "An integer from 0 to 100 indicating confidence in the predicted category, sub_category, and civic_agency.",
  "severity": "low | medium | high"
}

Rules:
- Use only the allowed values from the provided option lists.
- Predict exactly one value for category, sub_category, and civic_agency.
- confidence must be an integer between 0 and 100.
- severity must be exactly one of: low, medium, high.
- Output valid JSON only.
- Do not add any extra text, markdown, comments, or explanation.
""".strip()

RETRIEVAL_VISION_RAG_PROMPT = """
You are an expert civic complaint classification expert for Bengaluru city.

NEW COMPLAINT TO CLASSIFY:
Title: {title}
Description: {description}

SIMILAR PAST COMPLAINTS (for reference):
{similar_complaints}

TASK: Predict the correct labels for the NEW complaint above.

Respond ONLY with valid JSON:
{
  "description": "A clear one-sentence summary of the issue.",
  "category": "One value from {{CATEGORY_PROMPT_OPTIONS}}",
  "sub_category": "One value from {{SUBCATEGORY_PROMPT_OPTIONS}}",
  "civic_agency": "One value from {{CIVIC_AGENCY_PROMPT_OPTIONS}}",
  "confidence": "An integer from 0 to 100 indicating confidence in the predicted category, sub_category, and civic_agency.",
  "severity": "low | medium | high"
}

Rules:
- Use only the allowed values from the provided option lists.
- Predict exactly one value for category, sub_category, and civic_agency.
- confidence must be an integer between 0 and 100.
- severity must be exactly one of: low, medium, high.
- Output valid JSON only.
- Do not add any extra text, markdown, comments, or explanation.
""".strip()