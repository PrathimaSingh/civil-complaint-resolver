from collections import defaultdict
from datetime import datetime
import pandas as pd
from langchain_core.messages import AIMessage

from civic_redressal.db.json_db import load_complaints_db
from civic_redressal.utils.util import calculate_metrics, show_confusion_matrix
from civic_redressal.workflow.state import ComplaintPredictionBatchState, ComplaintPredictionState, ComplaintState


def run_analytics_agent(state: ComplaintState) -> dict:
    db = load_complaints_db()
    total = len(db)
    open_count = sum(1 for v in db.values() if v.get("status") == "open")
    closed_count = total - open_count

    type_count = defaultdict(int)
    subtype_count = defaultdict(int)
    authority_count = defaultdict(int)
    category_count = defaultdict(lambda: {"total": 0, "open": 0, "closed": 0})

    for v in db.values():
        ctype = v.get("type", "other")
        csubtype = v.get("subtype", "other")
        cauthority = v.get("authority", "Other")
        status = v.get("status", "open")

        type_count[ctype] += 1
        subtype_count[csubtype] += 1
        authority_count[cauthority] += 1
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
        "last_updated": datetime.now().isoformat(),
    }

    # Pretty Console Output
    print(f"\n{'='*60}")
    print("COMPLAINT ANALYTICS")
    print(f"{'='*60}")
    print(f"Total Complaints      : {total}")
    print(f"Open Complaints       : {open_count}")
    print(f"Closed Complaints     : {closed_count}")

    print("\nBreakdown by Authority:")
    print("-" * 50)
    for auth, count in sorted(authority_count.items(), key=lambda x: x[1], reverse=True):
        print(f"{auth:<25} | Total: {count:>3}")

    print("\nBreakdown by Category:")
    print("-" * 50)
    for cat, data in category_count.items():
        print(f"{cat:<25} | Total: {data['total']:>3} | Open: {data['open']:>3} | Closed: {data['closed']:>3}")

    print(f"\nLast Updated: {analytics['last_updated']}")
    print(f"{'='*60}\n")

    return {
        "analytics": analytics,
        "messages": [AIMessage(content="Analytics generated for dashboard.")],
    }

def run_prediction_analytics_agent(state: ComplaintPredictionBatchState) -> dict:
    # Placeholder for prediction analytics logic
    print("Running prediction analytics agent...")
    print("STATE KEYS:", state.keys())
    print("analytics agent - validation file path: ", state.get("validation_file_path"))

    df_validation = pd.read_csv(state.get("validation_file_path"))
    # Here you would compare the predictions with the actual labels in the validation set and calculate metrics like accuracy, precision, recall, F1-score, etc.
    category_actual = df_validation["category_title"].tolist()
    category_predicted = [complaint.get("predicted_category") for complaint in state.get("complaints", [])]
    if "sub_category_title" in df_validation.columns:
        sub_category_actual = df_validation["sub_category_title"].tolist()
        sub_category_predicted = [complaint.get("predicted_sub_category") for complaint in state.get("complaints", [])]
    else:
        print("No sub-category labels found in validation set, skipping sub-category analytics.")
        sub_category_actual = []
        sub_category_predicted = []
    civic_agency_actual = df_validation["civic_agency_title"].tolist()
    civic_agency_predicted = [complaint.get("predicted_civic_agency") for complaint in state.get("complaints", [])]

    print("Show confusion matrix for category prediction")
    show_confusion_matrix(category_actual, category_predicted, labels=list(set(category_actual)), title="Category Prediction Confusion Matrix")
    if "sub_category_title" in df_validation.columns:
        print("Show confusion matrix for sub-category prediction")
        show_confusion_matrix(sub_category_actual, sub_category_predicted, labels=list(set(sub_category_actual)), title="Sub-category Prediction Confusion Matrix")
    print("Show confusion matrix for civic agency prediction")
    show_confusion_matrix(civic_agency_actual, civic_agency_predicted, labels=list(set(civic_agency_actual)), title="Civic Agency Prediction Confusion Matrix")

    category_metrics = calculate_metrics(category_actual, category_predicted)
    if "sub_category_title" in df_validation.columns:
        sub_category_metrics = calculate_metrics(sub_category_actual, sub_category_predicted)
    civic_agency_metrics = calculate_metrics(civic_agency_actual, civic_agency_predicted)

    print("\nPREDICTION ANALYTICS")
    print("-" * 50)
    print(f"Category Prediction - Accuracy: {category_metrics['accuracy']:.2f}, Precision: {category_metrics['precision']:.2f}, Recall: {category_metrics['recall']:.2f}, F1-Score: {category_metrics['f1_score']:.2f}")
    if "sub_category_title" in df_validation.columns:
        print(f"Sub-category Prediction - Accuracy: {sub_category_metrics['accuracy']:.2f}, Precision: {sub_category_metrics['precision']:.2f}, Recall: {sub_category_metrics['recall']:.2f}, F1-Score: {sub_category_metrics['f1_score']:.2f}")
    print(f"Civic Agency Prediction - Accuracy: {civic_agency_metrics['accuracy']:.2f}, Precision: {civic_agency_metrics['precision']:.2f}, Recall: {civic_agency_metrics['recall']:.2f}, F1-Score: {civic_agency_metrics['f1_score']:.2f}")

    return {
        "prediction_analytics": {
            "category_metrics": category_metrics,
            "sub_category_metrics": sub_category_metrics if "sub_category_title" in df_validation.columns else {},
            "civic_agency_metrics": civic_agency_metrics,
        },
        "messages": [AIMessage(content="Prediction analytics generated for dashboard.")],
    }
