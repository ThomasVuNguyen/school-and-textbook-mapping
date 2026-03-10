#!/usr/bin/env python3
import csv
import json
import collections

def main():
    schools = []
    
    # State mapping for proper names
    state_names = {
      "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", 
      "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", 
      "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", 
      "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", 
      "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", 
      "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", 
      "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", 
      "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", 
      "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", 
      "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", 
      "DC": "District of Columbia", "PR": "Puerto Rico", "GU": "Guam"
    }

    stats = {
        "total": 0,
        "hasIA": 0,
        "noIA": 0,
        "verified": 0,
        "withUrls": 0,
        "states": 0
    }

    state_counts = collections.defaultdict(lambda: {"total": 0, "hasIA": 0, "noIA": 0})
    control_counts = collections.defaultdict(lambda: {"total": 0, "hasIA": 0, "noIA": 0})
    level_counts = collections.defaultdict(lambda: {"total": 0, "hasIA": 0, "noIA": 0})
    partner_counts = collections.Counter()
    program_counts = collections.Counter()
    flat_rates = []

    with open("verified_dataset.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total"] += 1
            has_ia = row.get("has_ia_program", "unknown").lower()
            
            if has_ia == "yes":
                stats["hasIA"] += 1
            elif has_ia == "no":
                stats["noIA"] += 1
                
            if row.get("source_url", "").strip():
                stats["withUrls"] += 1
                
            if row.get("confidence") == "verified":
                stats["verified"] += 1

            st = row.get("state", "").upper()
            state_counts[st]["total"] += 1
            if has_ia == "yes":
                state_counts[st]["hasIA"] += 1
            elif has_ia == "no":
                state_counts[st]["noIA"] += 1

            ctrl = row.get("control", "other")
            control_counts[ctrl]["total"] += 1
            if has_ia == "yes":
                control_counts[ctrl]["hasIA"] += 1
            elif has_ia == "no":
                control_counts[ctrl]["noIA"] += 1

            lvl = row.get("level", "other")
            level_counts[lvl]["total"] += 1
            if has_ia == "yes":
                level_counts[lvl]["hasIA"] += 1
            elif has_ia == "no":
                level_counts[lvl]["noIA"] += 1

            partner = row.get("bookstore_partner", "").strip()
            if has_ia == "yes" and partner:
                partner_counts[partner] += 1
                
            program = row.get("ia_program_name", "").strip()
            if has_ia == "yes" and program:
                program_counts[program] += 1
                
            cost_model = row.get("ia_cost_model", "").strip()
            price_str = row.get("ia_price", "").strip()
            
            if has_ia == "yes" and cost_model in ("flat-rate-semester", "flat-rate-credit"):
                try:
                    price_val = float(''.join(c for c in price_str if c.isdigit() or c == '.')) if price_str else 0.0
                    if price_val > 0:
                        flat_rates.append({
                            "school": row["school_name"],
                            "state": st,
                            "program": program,
                            "type": "per_semester" if "semester" in cost_model else "per_credit",
                            "price": price_val
                        })
                except ValueError:
                    pass

            try:
                enroll = int(float(row.get("enrollment") or 0))
            except:
                enroll = 0

            schools.append({
                "name": row["school_name"],
                "state": st,
                "city": row.get("city", ""),
                "control": ctrl,
                "level": lvl,
                "enrollment": enroll,
                "ia": has_ia,
                "program": program,
                "partner": partner,
                "cost_model": cost_model,
                "cost_price": price_str,
                "opt_out": row.get("ia_opt_out", "").strip(),
                "oer": row.get("oer_program", "").strip(),
                "url": row.get("source_url", "").strip(),
                "confidence": row.get("confidence", "unverified"),
                "verification_date": row.get("verification_date", "")
            })

    stats["states"] = len([s for s in state_counts.keys() if s in state_names])

    byState = []
    for st, counts in state_counts.items():
        if st in state_names:
            t = counts["total"]
            byState.append({
                "state": st,
                "name": state_names[st],
                "total": t,
                "hasIA": counts["hasIA"],
                "noIA": counts["noIA"],
                "rate": round(counts["hasIA"] / t * 100, 1) if t > 0 else 0
            })

    byControl = []
    for ctrl, counts in control_counts.items():
        if ctrl:
            t = counts["total"]
            byControl.append({
                "control": ctrl,
                "total": t,
                "hasIA": counts["hasIA"],
                "noIA": counts["noIA"],
                "rate": round(counts["hasIA"] / t * 100, 1) if t > 0 else 0
            })
            
    byLevel = []
    for lvl, counts in level_counts.items():
        if lvl:
            t = counts["total"]
            byLevel.append({
                "level": lvl,
                "total": t,
                "hasIA": counts["hasIA"],
                "noIA": counts["noIA"],
                "rate": round(counts["hasIA"] / t * 100, 1) if t > 0 else 0
            })

    top_partners = [{"partner": k, "count": v} for k, v in partner_counts.most_common(10) if k and k.lower() not in ("unknown", "?", "n/a")]
    top_programs = [{"name": k, "count": v} for k, v in program_counts.most_common(15) if k and k.lower() not in ("unknown", "?", "n/a", "inclusive access", "first day")]

    out = {
        "stats": stats,
        "byState": sorted(byState, key=lambda x: x["state"]),
        "byControl": sorted(byControl, key=lambda x: x["total"], reverse=True),
        "byLevel": sorted(byLevel, key=lambda x: x["total"], reverse=True),
        "partners": top_partners,
        "topPrograms": top_programs,
        "flatRates": sorted(flat_rates, key=lambda x: x["price"]),
        "schools": schools
    }

    with open("dashboard_v2_data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
        
    print(f"Generated dashboard_v2_data.json with {len(schools)} schools.")

if __name__ == "__main__":
    main()
