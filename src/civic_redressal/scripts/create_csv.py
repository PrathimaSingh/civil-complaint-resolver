import os
import csv

# Define the directory path
directory_path = r'D:\StudyStuff\PES MTech\Sem3\GroupProjects\Projects\CiviFixDemo--PES\data\Street-Light-Dataset-main\Raw Dataset\Not Working'

# Initialize a list to store rows for the CSV
rows = []

# Iterate over all files in the directory
for filename in os.listdir(directory_path):
    if filename.endswith(".jpg") or filename.endswith(".png"):  # Adjust extensions as needed
        image_path = os.path.join(directory_path, filename)
        row = {
            "id": len(rows) + 1,
            "image_path": filename,
            "category_title": "Mobility - Roads, Footpaths and Infrastructure",
            "civic_agency_title": "BBMP",
        }
        rows.append(row)

# Define the CSV file path
csv_file_path = 'street_light_data.csv'

# Write the data to a CSV file
with open(csv_file_path, mode='w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=["id", "image_path", "category_title", "civic_agency_title"])
    
    # Write the header row
    writer.writeheader()
    
    # Write the data rows
    for row in rows:
        writer.writerow(row)

print(f"CSV file '{csv_file_path}' created successfully.")