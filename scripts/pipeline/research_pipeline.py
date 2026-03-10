#!/usr/bin/env python3
"""
Gemini CLI Research Pipeline
─────────────────────────────
Uses Gemini CLI (free, headless mode) to research Inclusive Access programs
for schools from us_colleges_master.csv.

Features:
  - Runs `gemini -p` in headless mode for each school
  - Parses structured JSON response
  - Resolves vertexaisearch redirect URLs to real URLs
  - Saves results to checkpoint CSV (resume-capable)
  - Rate-limited to avoid quota issues

Usage:
  python3 research_pipeline.py                    # default 10 schools
  python3 research_pipeline.py --batch-size 50    # custom batch size
  python3 research_pipeline.py --resume           # resume from checkpoint
"""

import csv
import json
import os
import re
import subprocess
import sys
import time
import argparse
import requests

# ── Config ────────────────────────────────────────────────────────────────────
INPUT_CSV = "data/reference/us_colleges_master.csv"
OUTPUT_CSV = "data/raw/research_results.csv"
CHECKPOINT_FILE = "data/raw/research_checkpoint.txt"  # tracks last processed index
DELAY_BETWEEN_CALLS = 5  # seconds between Gemini CLI calls

PROMPT_TEMPLATE = """Research the inclusive access (IA) textbook program at {school_name} ({state}).

Search for: "{school_name} inclusive access textbook program", "{school_name} bookstore day one access", "{school_name} course materials fee".

Return ONLY a valid JSON object (no markdown, no explanation, no extra text) with exactly these fields:
{{
  "ia_program": "program name or None found",
  "cost_model": "per-course or flat-rate or included-tuition or unknown",
  "price": "price info or Not listed",
  "source_url": "most relevant URL found",
  "confidence": "HIGH or MEDIUM or LOW",
  "summary": "1-2 sentence summary of findings"
}}
"""

OUTPUT_FIELDS = [
    "unitid", "school_name", "state", "city", "sector",
    "ia_program", "cost_model", "price", "source_url",
    "confidence", "summary", "raw_source_url", "researched_at",
]


def resolve_redirect_url(url: str, timeout: int = 5) -> str:
    """Resolve vertexaisearch redirect URLs to actual destination URLs."""
    if not url or not isinstance(url, str):
        return url
    try:
        resp = requests.head(url, allow_redirects=True, timeout=timeout)
        return resp.url
    except Exception:
        # If redirect resolution fails, try GET as fallback
        try:
            resp = requests.get(url, allow_redirects=True, timeout=timeout, stream=True)
            final = resp.url
            resp.close()
            return final
        except Exception:
            return url  # return original on failure


def call_gemini_cli(school_name: str, state: str) -> dict:
    """Call Gemini CLI in headless mode and parse JSON response."""
    prompt = PROMPT_TEMPLATE.format(school_name=school_name, state=state)

    try:
        result = subprocess.run(
            ["gemini", "-p", prompt, "-o", "text", "--sandbox", "false"],
            capture_output=True,
            text=True,
            timeout=90,  # 90s timeout per school
            cwd="/tmp",  # avoid loading project files
        )
        output = result.stdout.strip()
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}

    # Extract JSON from output (may have preamble text before the JSON)
    json_match = re.search(r'\{[^{}]*\}', output, re.DOTALL)
    if not json_match:
        # Try to find JSON with nested objects
        json_match = re.search(r'\{.*\}', output, re.DOTALL)

    if json_match:
        try:
            data = json.loads(json_match.group())
            return data
        except json.JSONDecodeError:
            return {"error": "json_parse_failed", "raw": output[:500]}

    return {"error": "no_json_found", "raw": output[:500]}


def load_schools(csv_path: str) -> list:
    """Load schools from the master CSV."""
    schools = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            schools.append(row)
    return schools


def load_checkpoint() -> int:
    """Load the last processed index from checkpoint file."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return int(f.read().strip())
    return 0


def save_checkpoint(index: int):
    """Save the current index to checkpoint file."""
    with open(CHECKPOINT_FILE, "w") as f:
        f.write(str(index))


def load_already_done() -> set:
    """Load unitids already researched from output CSV."""
    done = set()
    if os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                done.add(row.get("unitid", ""))
    return done


def append_result(result: dict):
    """Append a single result to the output CSV."""
    file_exists = os.path.exists(OUTPUT_CSV)
    with open(OUTPUT_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(result)


def main():
    parser = argparse.ArgumentParser(description="Gemini CLI IA Research Pipeline")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of schools to process")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--start", type=int, default=0, help="Starting index in CSV")
    args = parser.parse_args()

    schools = load_schools(INPUT_CSV)
    already_done = load_already_done()

    start_idx = args.start
    if args.resume:
        start_idx = load_checkpoint()

    batch_size = args.batch_size
    end_idx = min(start_idx + batch_size, len(schools))

    print("=" * 70)
    print(f"Gemini CLI IA Research Pipeline")
    print(f"Schools in CSV: {len(schools)}")
    print(f"Already researched: {len(already_done)}")
    print(f"Processing: index {start_idx} → {end_idx} ({end_idx - start_idx} schools)")
    print(f"Delay between calls: {DELAY_BETWEEN_CALLS}s")
    print("=" * 70)

    success = 0
    fail = 0
    skipped = 0

    for i in range(start_idx, end_idx):
        school = schools[i]
        name = school["school_name"]
        state = school["state"]
        unitid = school["unitid"]

        if unitid in already_done:
            print(f"\n[{i+1}/{end_idx}] SKIP (already done): {name}")
            skipped += 1
            save_checkpoint(i + 1)
            continue

        print(f"\n[{i+1}/{end_idx}] Researching: {name} ({state})...")
        t0 = time.time()

        # Call Gemini CLI
        data = call_gemini_cli(name, state)
        elapsed = time.time() - t0

        if "error" in data:
            print(f"  ❌ ERROR ({elapsed:.1f}s): {data['error']}")
            if "raw" in data:
                print(f"  Raw output: {data['raw'][:200]}")
            fail += 1
            save_checkpoint(i + 1)
            time.sleep(DELAY_BETWEEN_CALLS)
            continue

        # Resolve redirect URL
        raw_url = data.get("source_url", "")
        print(f"  📡 Resolving URL: {raw_url[:80]}...")
        resolved_url = resolve_redirect_url(raw_url)
        if resolved_url != raw_url:
            print(f"  🔗 Resolved to: {resolved_url[:80]}")

        # Build result row
        result = {
            "unitid": unitid,
            "school_name": name,
            "state": state,
            "city": school.get("city", ""),
            "sector": school.get("sector", ""),
            "ia_program": data.get("ia_program", ""),
            "cost_model": data.get("cost_model", ""),
            "price": data.get("price", ""),
            "source_url": resolved_url,
            "confidence": data.get("confidence", ""),
            "summary": data.get("summary", ""),
            "raw_source_url": raw_url,
            "researched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        append_result(result)

        program = data.get("ia_program", "?")
        conf = data.get("confidence", "?")
        print(f"  ✅ ({elapsed:.1f}s) {program} | {conf}")
        success += 1

        save_checkpoint(i + 1)

        # Rate limit
        if i < end_idx - 1:
            print(f"  ⏳ Waiting {DELAY_BETWEEN_CALLS}s...")
            time.sleep(DELAY_BETWEEN_CALLS)

    print(f"\n{'=' * 70}")
    print(f"BATCH COMPLETE: {success} ✅ | {fail} ❌ | {skipped} skipped")
    print(f"Results saved to: {OUTPUT_CSV}")
    print(f"Checkpoint at index: {end_idx}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
