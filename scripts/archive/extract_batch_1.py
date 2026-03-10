import csv

INPUT_FILE = "verified_dataset.csv"
OUTPUT_FILE = "batch_1_top_200.csv"

def extract_top_schools():
    schools = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                enrollment = int(row.get("enrollment", 0))
            except ValueError:
                enrollment = 0
            row["_sort_enrollment"] = enrollment
            schools.append(row)
            
    # Sort by enrollment descending
    schools.sort(key=lambda x: x["_sort_enrollment"], reverse=True)
    
    # Grab Top 200
    top_200 = schools[:200]
    
    # Write to new file
    if not top_200:
        print("No schools found.")
        return
        
    # Remove our temporary sort key
    for row in top_200:
        del row["_sort_enrollment"]
        
    headers = list(top_200[0].keys())
    
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in top_200:
            writer.writerow(row)
            
    print(f"Extracted top {len(top_200)} schools by enrollment to {OUTPUT_FILE}.")

if __name__ == "__main__":
    extract_top_schools()
