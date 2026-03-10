import csv

MASTER_FILE = "us_colleges_master.csv"
RESEARCH_FILE = "access_code_research_results.csv"
OUTPUT_FILE = "verified_dataset.csv"

def prep_dataset():
    # 1. Load enrollment from master
    enrollment_map = {}
    with open(MASTER_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("INSTNM", "").strip()
            state = row.get("STABBR", "").strip()
            try:
                enrollment_map[(name, state)] = int(row.get("ENROLL", 0) or 0)
            except ValueError:
                enrollment_map[(name, state)] = 0

    # 2. Read research data
    existing_schools = []
    with open(RESEARCH_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing_schools.append(row)

    headers = [
        "school_name", "state", "city", "control", "level", "enrollment",
        "has_ia_program", "ia_program_name", "ia_cost_model", "ia_price",
        "ia_opt_out", "bookstore_partner", "publishers_platforms", "oer_program",
        "source_url", "source_type", "verification_date", "confidence", "notes"
    ]

    # 3. Write new CSV
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        
        assigned = 0
        for row in existing_schools:
            school_name = row.get("school_name", "").strip()
            state = row.get("state", "").strip()
            
            # Lookup enrollment
            enrollment = enrollment_map.get((school_name, state), 0)
            
            url = row.get("source_urls", "").strip()
            if url.lower() == "n/a": url = ""
            has_url = bool(url)
            
            new_row = {
                "school_name": school_name,
                "state": state,
                "city": row.get("city", ""),
                "control": row.get("control", ""),
                "level": row.get("level", ""),
                "enrollment": enrollment,
                "has_ia_program": row.get("has_inclusive_access", "unknown"),
                "ia_program_name": row.get("program_name", ""),
                "ia_cost_model": row.get("cost_model", "unknown").lower() if row.get("cost_model") else "unknown",
                "ia_price": "", 
                "ia_opt_out": "unknown",
                "bookstore_partner": row.get("bookstore_partner", "unknown"),
                "publishers_platforms": row.get("publishers_used", ""),
                "oer_program": row.get("oer_program", "unknown"),
                "source_url": url,
                "source_type": "",
                "verification_date": "2026-03-09" if has_url else "",
                "confidence": "likely" if has_url else "unverified",
                "notes": row.get("notes", "")
            }
            writer.writerow(new_row)
            assigned += 1
            
    print(f"Successfully wrote {assigned} records to {OUTPUT_FILE}.")

if __name__ == "__main__":
    prep_dataset()
