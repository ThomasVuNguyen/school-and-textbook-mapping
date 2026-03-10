#!/usr/bin/env python3
"""
check_board.py — Check the current progress of the School Verification Kanban board.

Usage: python3 check_board.py
"""
import subprocess, json, os
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

DB_ID = "31fb11a2-332a-81a8-afcf-e21dbe68e8a3"
TOKEN = os.getenv("NOTION_TOKEN")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(SCRIPT_DIR, ".board_snapshot.json")

def fetch_all_pages():
    """Fetch all pages from the Notion database (handles pagination)."""
    all_pages = []
    start_cursor = None
    while True:
        payload = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor
        result = subprocess.run(
            ["curl", "-s", "--max-time", "15",
             f"https://api.notion.com/v1/databases/{DB_ID}/query",
             "-H", f"Authorization: Bearer {TOKEN}",
             "-H", "Content-Type: application/json",
             "-H", "Notion-Version: 2022-06-28",
             "-d", json.dumps(payload)],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        all_pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        start_cursor = data.get("next_cursor")
    # Save snapshot
    with open(SNAPSHOT, "w") as f:
        json.dump({"results": all_pages}, f)
    return all_pages

def main():
    pages = fetch_all_pages()
    statuses = Counter()
    by_status = {}

    for p in pages:
        props = p.get("properties", {})
        title = props.get("School Name", {}).get("title", [])
        name = title[0]["plain_text"] if title else "?"
        status_obj = props.get("Status", {}).get("select")
        status = status_obj["name"] if status_obj else "No Status"
        statuses[status] += 1
        by_status.setdefault(status, []).append(name)

    total = sum(statuses.values())
    done = statuses.get("Done", 0)
    review = statuses.get("Review", 0)
    in_prog = statuses.get("In Progress", 0)
    not_started = statuses.get("Not Started", 0)
    touched = done + review + in_prog
    pct = (touched / total * 100) if total else 0

    print(f"\n{'='*50}")
    print(f"  SCHOOL VERIFICATION BOARD — PROGRESS REPORT")
    print(f"{'='*50}")
    print(f"  Total tickets:   {total}")
    print(f"  ✅ Done:          {done}")
    print(f"  👀 Review:        {review}")
    print(f"  🔄 In Progress:   {in_prog}")
    print(f"  ⬜ Not Started:   {not_started}")
    print(f"  ❓ No Status:     {statuses.get('No Status', 0)}")
    print(f"  {'─'*30}")
    print(f"  Progress: {touched}/{total} touched ({pct:.1f}%)")
    print(f"{'='*50}")

    for label, emoji in [("Done", "✅"), ("Review", "👀"), ("In Progress", "🔄")]:
        if label in by_status:
            print(f"\n{emoji} {label}:")
            for name in sorted(by_status[label]):
                print(f"   • {name}")

    print()

if __name__ == "__main__":
    main()
