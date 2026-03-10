#!/usr/bin/env python3
"""
Update the 10 schools from Codex batch 2 that were researched but never written to Notion.
Codex did the web research, but stream disconnects prevented Notion updates.
This script applies those results directly.
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = "31fb11a2-332a-81a8-afcf-e21dbe68e8a3"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# Research results from Codex batch 2 (captured from output monitoring)
SCHOOLS = [
    {
        "name": "University of Minnesota-Twin Cities",
        "ia_program": "Course Works Complete",
        "cost_model": "flat-rate-semester",
        "price": "$279/semester",
        "source_url": "https://bookstores.umn.edu/course-works-complete",
        "ai_results": "Searched: 'University of Minnesota Twin Cities inclusive access program textbook'. UMN offers Course Works Complete through UMN Bookstores—a flat-rate $279/semester plan giving unlimited access to required digital course materials. Auto-enrolled; opt-out available. Previously called Gopher Textbooks Unlimited. Confidence: HIGH.",
        "agent_notes": "Strong IA program with published pricing. Flat-rate semester model."
    },
    {
        "name": "Texas State University",
        "ia_program": "BookSmart @ TXST",
        "cost_model": "flat-rate-semester",
        "price": "$249/semester",
        "source_url": "https://news.txst.edu/inside-txst/2023/txst-to-launch-booksmart-to-reduce-student-expenses.html",
        "ai_results": "Searched: 'Texas State University inclusive access program textbook billing bursar'. Texas State launched BookSmart @ TXST—a $249/semester flat-rate program bundled with tuition. Students auto-enrolled; opt-out available. Covers all required course materials. Official news release from 2023 confirms. Confidence: HIGH.",
        "agent_notes": "Clear IA program with published flat-rate pricing. Well-documented."
    },
    {
        "name": "Louisiana State University and Agricultural & Mechanical College",
        "ia_program": "None found",
        "cost_model": "unknown",
        "price": "Not listed",
        "source_url": "https://www.lsu.edu/learningcenter/oer/",
        "ai_results": "Searched: 'Louisiana State University inclusive access bookstore program', 'LSU Bookstore inclusive access First Day program', 'Barnes & Noble LSU bookstore First Day program'. No evidence of a campus-wide inclusive access or First Day program at LSU. The library promotes OER and some e-textbook initiatives but no billable IA program found. Confidence: LOW.",
        "agent_notes": "No IA billing program found. LSU promotes OER/library alternatives instead."
    },
    {
        "name": "Brigham Young University-Idaho",
        "ia_program": "Auto Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.byui.edu/financial-services/student-accounts-receivable",
        "ai_results": "Searched: 'BYU-Idaho inclusive access program textbook fee'. BYU-Idaho offers Auto Access—an inclusive access program where digital course materials are automatically billed to student accounts per course. Students can opt out. Prices vary by course/textbook. Confidence: MEDIUM.",
        "agent_notes": "Per-course IA with opt-out. No fixed campus-wide price."
    },
    {
        "name": "Purdue University Global",
        "ia_program": "Books & Materials Included (Undergraduate)",
        "cost_model": "included-tuition",
        "price": "Not listed (included in tuition)",
        "source_url": "https://www.purdueglobal.edu/tuition-financial-aid/",
        "ai_results": "Searched: 'Purdue University Global inclusive access course materials fee'. Purdue Global includes books and materials automatically in undergraduate tuition. No separate fee or opt-out—materials are bundled into the standard tuition rate. Confidence: MEDIUM.",
        "agent_notes": "Tuition-embedded model for undergrads. Not a traditional opt-out IA program."
    },
    {
        "name": "The University of Alabama",
        "ia_program": "None found",
        "cost_model": "unknown",
        "price": "Not listed",
        "source_url": "https://supplystore.ua.edu/faq",
        "ai_results": "Searched: 'University of Alabama inclusive access program textbook billed to student account'. No inclusive access program found at UA Tuscaloosa. UA Supply Store FAQ states they do not charge student accounts for textbooks. Note: UAB and UAH (separate campuses) DO have IA programs, but the main Tuscaloosa campus does not. Confidence: MEDIUM.",
        "agent_notes": "No IA at Tuscaloosa campus. UAB/UAH have separate IA programs."
    },
    {
        "name": "Florida International University",
        "ia_program": "Panther Book Pack",
        "cost_model": "per-credit-hour",
        "price": "$20.50/credit hour",
        "source_url": "https://onestop.fiu.edu/finances/types-of-aid/panther-book-pack/",
        "ai_results": "Searched: 'Florida International University inclusive access program textbook billing bursar'. FIU offers Panther Book Pack at $20.50/credit hour, auto-enrolled via student account charges. Students can opt out. Covers all required course materials. FIU OneStop is the official info source. Confidence: HIGH.",
        "agent_notes": "Strong IA program with clear per-credit pricing. Well-documented on FIU OneStop."
    },
    {
        "name": "California State University-Fullerton",
        "ia_program": "Titan Direct Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.fullerton.edu/it/students/titan-direct-access.php",
        "ai_results": "Searched: 'California State University Fullerton inclusive access program textbook billing'. CSUF offers Titan Direct Access—an inclusive access program where digital materials are automatically billed per course after add/drop unless opted out. Prices vary by course. Transitioning to SmartAccess+ in the future. Confidence: MEDIUM.",
        "agent_notes": "Per-course IA with opt-out. No fixed pricing—varies by course. Transitioning to SmartAccess+."
    },
    {
        "name": "University of California-San Diego",
        "ia_program": "Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://blink.ucsd.edu/facilities/services/bookstore/inclusive-access.html",
        "ai_results": "Searched: 'UC San Diego inclusive access program textbook billed to student account'. UCSD offers Inclusive Access through the campus bookstore. Students get free access during add/drop; charges post to student account 3-4 weeks after term starts unless opted out. Prices vary by course. Confidence: MEDIUM.",
        "agent_notes": "Per-course IA with opt-out and grace period. No campus-wide flat rate."
    },
    {
        "name": "Ivy Tech Community College",
        "ia_program": "Ivy+ Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.ivytech.edu/bookstore/",
        "ai_results": "Searched: 'Ivy Tech inclusive access program textbook fee billed to student account'. Ivy Tech offers Ivy+ Access—an inclusive access program where digital course materials are automatically provided and billed per course. Students can opt out. Prices vary by course/section. Confidence: MEDIUM.",
        "agent_notes": "Per-course IA with opt-out. Prices vary by course."
    }
]

# Map cost model strings to Notion select values
COST_MODEL_MAP = {
    "flat-rate-semester": "flat-rate-semester",
    "per-course": "per-course", 
    "per-credit-hour": "per-credit-hour",
    "included-tuition": "included-tuition",
    "unknown": "unknown"
}

def find_page_by_name(name):
    """Find a page in the database by school name."""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "School Name",
            "title": {"equals": name}
        }
    }
    r = requests.post(url, headers=HEADERS, json=payload)
    data = r.json()
    if data.get("results"):
        return data["results"][0]["id"]
    return None

def update_page(page_id, school):
    """Update a Notion page with research results."""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    
    properties = {
        "Status": {"select": {"name": "Review"}},
        "IA Program Name": {"rich_text": [{"text": {"content": school["ia_program"]}}]},
        "Cost Model": {"select": {"name": COST_MODEL_MAP.get(school["cost_model"], "unknown")}},
        "Price": {"rich_text": [{"text": {"content": school["price"]}}]},
        "Source URL": {"url": school["source_url"]},
        "AI Research Results": {"rich_text": [{"text": {"content": school["ai_results"][:2000]}}]},
        "Agent Notes": {"rich_text": [{"text": {"content": school["agent_notes"]}}]}
    }
    
    r = requests.patch(url, headers=HEADERS, json={"properties": properties})
    return r.status_code == 200, r.json()

def main():
    print("=" * 60)
    print("  Updating 10 schools from Codex batch 2")
    print("=" * 60)
    
    success = 0
    failed = 0
    
    for school in SCHOOLS:
        name = school["name"]
        print(f"\n🔍 Finding: {name}...")
        page_id = find_page_by_name(name)
        
        if not page_id:
            print(f"  ❌ NOT FOUND in database!")
            failed += 1
            continue
        
        print(f"  📝 Updating page {page_id}...")
        ok, result = update_page(page_id, school)
        
        if ok:
            print(f"  ✅ Updated — Status: Review, IA: {school['ia_program']}")
            success += 1
        else:
            print(f"  ❌ FAILED: {json.dumps(result, indent=2)}")
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"  Results: {success} updated, {failed} failed")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
