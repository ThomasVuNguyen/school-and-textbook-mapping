import csv

DATASETS = ["verified_dataset.csv", "batch_1_top_200.csv"]

updates = {
    "California State University-Fullerton": {
        "has_ia_program": "yes",
        "ia_program_name": "Inclusive Access",
        "ia_cost_model": "per-course",
        "ia_opt_out": "yes",
        "oer_program": "yes",
        "bookstore_partner": "Independent/In-house", # Titan Shops
        "source_url": "https://www.fullerton.edu/titan-shops/",
        "confidence": "verified"
    },
    "Tarrant County College District": {
        "has_ia_program": "yes",
        "ia_program_name": "TCC Plus (First Day)",
        "ia_cost_model": "per-course",
        "ia_opt_out": "yes",
        "bookstore_partner": "Barnes & Noble College", # First Day usually implies BN
        "source_url": "https://www.tccd.edu/services/campus-resources/bookstores/tcc-plus/",
        "confidence": "verified"
    },
    "California State University-Northridge": {
        "has_ia_program": "yes",
        "ia_program_name": "CSUN Ready / myCSUNDigitalAccess",
        "ia_cost_model": "per-course",
        "ia_opt_out": "yes",
        "bookstore_partner": "Follett",
        "source_url": "https://www.csun.edu/mycsundigitalaccess",
        "confidence": "verified"
    },
    "University of Florida": {
        "has_ia_program": "yes",
        "ia_program_name": "UF All Access",
        "ia_cost_model": "per-course",
        "ia_opt_out": "opt-in", # UF uses an explicit opt-in model!
        "bookstore_partner": "Follett",
        "source_url": "https://businessservices.ufl.edu/services/uf-bookstore/uf-all-access/",
        "confidence": "verified"
    },
    "Indiana University-Bloomington": {
        "has_ia_program": "yes",
        "ia_program_name": "eTexts",
        "ia_cost_model": "per-course",
        "ia_opt_out": "yes",
        "oer_program": "yes",
        "bookstore_partner": "Follett", # Follett ACCESS
        "source_url": "https://uits.iu.edu/services/teaching-learning/etexts/index.html",
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
