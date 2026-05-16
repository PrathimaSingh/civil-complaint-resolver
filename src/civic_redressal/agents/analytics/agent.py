from collections import defaultdict
from datetime import datetime
from langchain_core.messages import AIMessage

from civic_redressal.db.json_db import load_complaints_db
from civic_redressal.workflow.state import ComplaintState


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
