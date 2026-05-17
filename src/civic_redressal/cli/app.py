import os

from civic_redressal.config import INCOMING_FOLDER
from civic_redressal.services.complaint_service import ingest_complaints_from_csv, process_new_complaint, process_new_complaint_rag, close_complaint
from civic_redressal.agents.analytics.agent import run_analytics_agent
from civic_redressal.utils.util import read_multiline_description
from civic_redressal.retrieval.complaint_repository import list_all_complaints

def show_menu():
    print("\n" + "="*80)
    print("Available Commands:")
    print("  new <image_path>                           -- Process new complaint from image")
    print("  text <title>|<description>                 -- Process new complaint from text")
    print("  rag <title>|<description>                  -- Process new complaint with RAG analysis")
    print("  ragimg <image_path>|<title>|<description>  -- Process new complaint with image captioning + RAG")
    print("  ingest <csv_path>                         -- Ingest complaints from CSV file")
    print("  close <ID> <resolved_path>                 -- Close a complaint")
    print("  analytics                                  -- Show analytics")
    print("  list                                       -- List all complaints")
    print("  exit                                       -- Quit")
    print("="*80)

def main():
    print("Civil Complaint Resolver System Started\n")

    # Process all images in incoming folder
    for filename in os.listdir(INCOMING_FOLDER):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            process_new_complaint(os.path.join(INCOMING_FOLDER, filename))

    while True:
        show_menu()
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
        
        elif cmd.startswith("ragimg"):
            parts = cmd[6:].split("|", 2)
            if len(parts) < 3:
                print("Usage: ragimg <image_path>|<title>|<description>")
                print("If title or description is not available, use empty string but keep the delimiters. Example: ragimg /path/to/image.jpg|""|""")
                continue
            image_path, title, description = parts
            print(f"Processing RAG with image. Image: {image_path}, Title: '{title}', Description: '{description}'")
            process_new_complaint_rag(title.strip(), description.strip(), image_path.strip())

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

        elif cmd.startswith("ingest"):
            path = cmd[6:].strip()
            csv_path = path if path else "complaints.csv"
            print("Enter the column name for title (leave blank for default: 'title'): ", end="")
            title_column = input().strip() or "title"
            print("Enter the column name for description (leave blank for default: 'description'): ", end="")
            description_column = input().strip() or "description"
            print("Enter the column name for image path (leave blank for default: 'image_path'): ", end="")
            image_column = input().strip() or "image_path"
            print("Enter the column name for category (leave blank for default: 'category'): ", end="")
            category_column = input().strip() or "category"
            print("Enter the column name for sub-category (leave blank for default: 'sub_category'): ", end="")
            sub_category_column = input().strip() or "sub_category"
            print("Enter the column name for civic agency (leave blank for default: 'civic_agency'): ", end="")
            civic_agency_column = input().strip() or "civic_agency"
            ingest_complaints_from_csv(csv_path, title_column, description_column, image_column, category_column, sub_category_column, civic_agency_column)

        elif cmd.startswith("close "):
            parts = cmd[6:].split()
            if len(parts) >= 2:
                close_complaint(parts[0], parts[1])
            else:
                print("Usage: close <ID> <resolved_image_path>")
        elif cmd == "analytics":
            run_analytics_agent({"image_path": ""})
        elif cmd == "list":
            list_all_complaints()
        else:
            print("Unknown command. Try: new, text, close, analytics, list, exit")

# ====================== MAIN ======================
if __name__ == "__main__":
    main()
