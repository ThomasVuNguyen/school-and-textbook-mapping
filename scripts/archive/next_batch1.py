import csv

with open("batch_1_top_200.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    unverified = []
    for row in reader:
        if row.get("confidence") != "verified":
            unverified.append(row)
            
    print(f"Total unverified in batch 1: {len(unverified)}")
    print("Next 10 to verify:")
    for row in unverified[:10]:
        print(f"- {row['school_name']} ({row['state']}) / Enrollment: {row.get('enrollment', '?')}")
