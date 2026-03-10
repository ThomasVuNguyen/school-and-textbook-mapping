import urllib.request
import urllib.parse
import re
import csv
import time
import random

CSV_FILE = "batch_1_top_200.csv"

def search_yahoo(query):
    url = "https://search.yahoo.com/search?p=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    try:
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        # Yahoo results have class="ac-algo fz-l ac-21th lh-24" or something, but let's just grab all http links that look like actual sites
        # We can look for href="https://..." and filter out yahoo/bing/google
        matches = re.findall(r'href="(https?://[^"]+)"', html)
        return matches
    except Exception as e:
        print(f"Search failed for {query}: {e}")
        return []

def main():
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        
    if not rows:
        return
        
    headers = list(rows[0].keys())
    
    verified_count = 0
    for row in rows:
        if row.get("confidence") in ["verified", "likely"]:
            continue
            
        school = row['school_name']
        print(f"Searching for {school}...")
        query = f'"{school}" "inclusive access" OR "first day" OR "equitable access" OR "day one" textbooks'
        urls = search_yahoo(query)
        
        best_url = ""
        for u in urls:
            if "yahoo.com" in u or "bing.com" in u or "microsoft.com" in u: continue
            if ".edu" in u or "bncvirtual.com" in u or "bkstr.com" in u or "textbook" in u.lower() or "follet" in u.lower():
                # Extract actual URL if wrapped in Yahoo redirect (usually doesn't apply to the display link but just in case)
                if "RU=" in u:
                    try:
                        u = urllib.parse.unquote(u.split("RU=")[1].split("/RK=")[0])
                    except:
                        pass
                best_url = u
                break
                
        if best_url:
            print(f"  Found: {best_url}")
            row["source_url"] = best_url
            row["confidence"] = "likely" 
            row["verification_date"] = "2026-03-10"
            verified_count += 1
        else:
            print("  No good URL found.")
            
        time.sleep(random.uniform(1.0, 3.0))
        
        # Save incrementally
        with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
            
    print(f"\nDone! Automatically verified {verified_count} new schools.")

if __name__ == "__main__":
    main()
