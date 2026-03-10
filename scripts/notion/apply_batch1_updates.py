import csv

updates = {
    "University of Illinois Urbana-Champaign": {"ia": "no", "program": "", "partner": "", "cost_model": "", "cost_price": "", "url": "none"},
    "California State University-Long Beach": {"ia": "yes", "program": "Day 1 Textbook Access", "partner": "", "cost_model": "flat_rate", "cost_price": "250", "url": "https://www.csulb.edu/student-affairs/inclusive-access"},
    "University of Wisconsin-Madison": {"ia": "no", "program": "", "partner": "", "cost_model": "", "cost_price": "", "url": "none"},
    "Florida State University": {"ia": "yes", "program": "Follett Access", "partner": "Follett", "cost_model": "", "cost_price": "", "url": "https://obs.fsu.edu/follett-access"},
    "University of California-San Diego": {"ia": "yes", "program": "Inclusive Access", "partner": "RedShelf", "cost_model": "", "cost_price": "", "url": "https://ucsandiegobookstore.com/inclusive-access"},
    "The University of Texas at Arlington": {"ia": "yes", "program": "First Day", "partner": "Barnes & Noble", "cost_model": "", "cost_price": "", "url": "https://www.uta.edu/business-affairs/bookstore/first-day"},
}

DATASET_FILE = "verified_dataset.csv"
output_rows = []
updated_count = 0

with open(DATASET_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames
    for row in reader:
        name = row["school_name"]
        if name in updates and row["confidence"] != "verified":
            upd = updates[name]
            row["ia"] = upd["ia"]
            row["program"] = upd["program"]
            row["partner"] = upd["partner"]
            row["cost_model"] = upd["cost_model"]
            row["cost_price"] = upd["cost_price"]
            row["url"] = upd["url"]
            row["confidence"] = "verified"
            updated_count += 1
        output_rows.append(row)

with open(DATASET_FILE, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"Updated {updated_count} schools to 'verified'.")
