import csv
import json
import time
import urllib.request

OUTPUT_FILE = "batch_1_top_200.csv"
DATASET_FILE = "verified_dataset.csv"

def fetch_top_200():
    print("Fetching largest schools by enrollment from College Scorecard API...")
    
    API_KEY = "DEMO_KEY"
    base_url = "https://api.data.gov/ed/collegescorecard/v1/schools.json"
    top_schools = []
    
    # We will fetch schools with > 25000 students (that should give us ~150-200 of the biggest)
    for page in range(3):
        print(f"Fetching page {page}...")
        url = f"{base_url}?2021.student.size__range=25000..&per_page=100&page={page}&fields=id,school.name,school.state,2021.student.size&api_key={API_KEY}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                results = data.get("results", [])
                if not results:
                    break
                top_schools.extend(results)
        except Exception as e:
            print(f"Error fetching data: {e}")
            break
            
        time.sleep(1) # Be nice to DEMO_KEY
        
    print(f"Found {len(top_schools)} massive schools from API.")
    
    # Sort by size descending just in case
    top_schools.sort(key=lambda x: x.get("2021.student.size", 0) or 0, reverse=True)
    
    # Load our verified dataset
    our_schools = {}
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            our_schools[(row["school_name"], row["state"])] = row
            
    # Match the Top against our database
    matched = []
    for s in top_schools:
        name = s.get("school.name", "")
        state = s.get("school.state", "")
        size = s.get("2021.student.size", 0)
        
        # Exact match
        if (name, state) in our_schools:
            row = our_schools[(name, state)].copy()
            row["enrollment"] = size
            matched.append(row)
            continue
            
        # Substring match
        found = False
        for (our_name, our_state), row in our_schools.items():
            if our_state == state and (name.lower() in our_name.lower() or our_name.lower() in name.lower()):
                matched_row = row.copy()
                matched_row["enrollment"] = size
                matched.append(matched_row)
                found = True
                break
                
        if not found:
            # print(f"Warning: Could not match {name} ({state}) in our database.")
            pass
            
    print(f"Successfully matched {len(matched)} of the massive schools.")
    
    if not matched: return
    
    # Write to CSV
    headers = list(matched[0].keys())
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in matched:
            writer.writerow(row)
            
    print(f"Saved {len(matched)} schools to {OUTPUT_FILE}")

if __name__ == "__main__":
    fetch_top_200()
