from datetime import datetime

def build_document_text(row):
    return " | ".join([
        f"Title: {row['title']}",
        f"Description: {row['description']}",
        f"Image Caption: {row['image_caption']}",
        f"Category: {row['category']}",
        f"Subcategory: {row['sub_category']}",
        f"Civic agency: {row['civic_agency']}",
    ])

def build_query(title="", description="", image_caption="", category="", sub_category="", civic_agency=""):
    parts = [
        f"Title: {title}" if title else "",
        f"Description: {description}" if description else "",
        f"Image Caption: {image_caption}" if image_caption else "",
        f"Category: {category}" if category else "",
        f"Subcategory: {sub_category}" if sub_category else "",
        f"Civic agency: {civic_agency}" if civic_agency else "",
    ]
    return " | ".join([p for p in parts if p.strip()])

def now_iso():
    return datetime.now().isoformat()