import csv

DATASETS = ["verified_dataset.csv", "batch_1_top_200.csv"]

updates = {
    "Southern New Hampshire University": {
        "has_ia_program": "yes",
        "ia_program_name": "SNHU Online Bookstore (BNC Virtual)",
        "ia_cost_model": "per-course",
        "bookstore_partner": "Barnes & Noble College",
        "source_url": "https://www.snhu.edu/admission/online/financial-aid/book-vouchers",
        "confidence": "verified"
    },
    "Western Governors University": {
        "has_ia_program": "yes",
        "ia_program_name": "Resource Fee",
        "ia_cost_model": "included-tuition",
        "ia_opt_out": "no",
        "bookstore_partner": "Independent/In-house",
        "source_url": "https://www.wgu.edu/financial-aid-tuition.html",
        "confidence": "verified"
    },
    "Ivy Tech Community College": {
        "has_ia_program": "yes",
        "ia_program_name": "Ivy+ Textbooks",
        "ia_cost_model": "flat-rate-credit",
        "ia_price": "$17/credit",
        "ia_opt_out": "yes",
        "bookstore_partner": "eCampus.com",
        "source_url": "https://www.ivytech.edu/tuition-aid/ivy-textbooks/",
        "confidence": "verified"
    },
    "Brigham Young University-Idaho": {
        "has_ia_program": "yes",
        "ia_program_name": "Auto Access",
        "ia_cost_model": "per-course",
        "ia_opt_out": "yes",
        "bookstore_partner": "University Bookstore",
        "source_url": "https://www.byui.edu/university-store/auto-access",
        "confidence": "verified"
    },
    "University of Maryland Global Campus": {
        "has_ia_program": "no",
        "oer_program": "yes",
        "bookstore_partner": "UMGC Online Bookstore",
        "source_url": "https://www.umgc.edu/current-students/finances/course-materials",
        "confidence": "verified"
    }
}

for filename in DATASETS:
    rows = []
    headers = []
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        for row in reader:
            name = row["school_name"]
            if name in updates:
                for k, v in updates[name].items():
                    row[k] = v
            rows.append(row)
            
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Updated {len(updates)} records in {filename}.")
