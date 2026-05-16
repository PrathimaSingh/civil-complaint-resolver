# Test / Initialization
from civic_redressal.retrieval.complaint_repository import list_all_complaints
from civic_redressal.retrieval.vectorstore import get_vectorstore


if __name__ == "__main__":
    print("=== Civil Complaint Vector Database ===")

    while True:
        cmd = input("\nEnter command (list/exit): ").strip().lower()
        if cmd in ['exit', 'quit', 'q']:
            break
        elif cmd == "list":
            vs = get_vectorstore()
            list_all_complaints()