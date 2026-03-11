#!/usr/bin/env python3
"""
verify_silver.py — Verify SILVER-tier schools using Cloudrift/Gemma 3.
────────────────────────────────────────────────────────────────────────
Reads silver_dataset.csv, runs 2-tier validation (HTTP + LLM), and
classifies each into VALIDATED / LIKELY_VALID / SUSPECT / URL_BROKEN / NO_URL.

KEY FEATURE: Fully interruptible & resumable via checkpoint file.
  - Progress saved after EVERY school to a checkpoint CSV.
  - On restart, already-verified schools are skipped automatically.
  - Ctrl+C at any time is safe — just re-run to continue.

Usage:
  source .venv/bin/activate
  python scripts/pipeline/verify_silver.py                    # run all
  python scripts/pipeline/verify_silver.py --batch-size 200   # do 200 at a time
  python scripts/pipeline/verify_silver.py --dry-run          # preview only
  python scripts/pipeline/verify_silver.py --reset            # wipe checkpoint, start fresh
  python scripts/pipeline/verify_silver.py --stats            # show progress so far
"""

import csv
import json
import os
import re
import sys
import time
import signal
import argparse
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from openai import OpenAI

# ─── Environment & Config ────────────────────────────────────────────────────

load_dotenv()

CLOUDRIFT_API_KEY  = os.getenv("CLOUDRIFT_API_KEY")
CLOUDRIFT_BASE_URL = os.getenv("CLOUDRIFT_BASE_URL", "https://llm-gateway.cloudrift.ai/v1")
CLOUDRIFT_MODEL    = os.getenv("CLOUDRIFT_MODEL", "google/gemma-3-12b-it")

BASE = os.path.join(os.path.dirname(__file__), "..", "..")

INPUT_CSV      = os.path.join(BASE, "data/validated/silver_dataset.csv")
CHECKPOINT_CSV = os.path.join(BASE, "data/validated/silver_verification_checkpoint.csv")
OUTPUT_CSV     = os.path.join(BASE, "data/validated/silver_verified.csv")

DELAY_BETWEEN   = 0.5      # seconds between API calls
HTTP_TIMEOUT    = 8         # seconds for URL check
LLM_TIMEOUT     = 30        # seconds for LLM call
PAGE_TEXT_MAX   = 2000       # max chars sent to LLM

# ─── Graceful shutdown ────────────────────────────────────────────────────────

_SHUTDOWN = False

def _signal_handler(sig, frame):
    global _SHUTDOWN
    _SHUTDOWN = True
    print("\n\n⚠️  Interrupt received — finishing current school then saving...\n")

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# ─── Column definitions ──────────────────────────────────────────────────────

INPUT_COLS = [
    "unitid", "school_name", "state", "city",
    "has_ia", "ia_program_name", "cost_model", "price",
    "source_url", "confidence", "notes",
    "data_source", "quality_tier", "consolidated_at",
]

VERIFY_COLS = INPUT_COLS + [
    "v_status",         # VALIDATED / LIKELY_VALID / SUSPECT / URL_BROKEN / NO_URL
    "v_score",          # 0-10 confidence from LLM
    "v_url_code",       # HTTP status code
    "v_notes",          # explanation
    "v_at",             # ISO timestamp
]

# ─── Keywords for text extraction ─────────────────────────────────────────────

IA_KEYWORDS = [
    "inclusive", "access", "textbook", "course material", "book",
    "opt out", "opt-out", "first day", "flat", "per credit",
    "digital", "rental", "follett", "barnes", "cengage", "pearson",
    "mcgraw", "openstax", "vitalsource", "redshelf",
]

# ─── LLM Prompt ──────────────────────────────────────────────────────────────

VERIFY_PROMPT = """You are a data validation assistant. Given a research result and the actual page text, determine if the page corroborates the research.

RESEARCH RESULT:
- School: {school_name} ({city}, {state})
- Has IA: {has_ia}
- IA Program: {ia_program_name}
- Cost Model: {cost_model}
- Price: {price}
- Notes: {notes}
- Source URL: {source_url}

PAGE CONTENT (from source URL):
{page_text}

Evaluate:
1. school_match: Does the page belong to or reference this school?
2. ia_mentioned: Does the page mention a textbook/course materials/inclusive access program?
3. program_match: Does the program name match the research result?
4. cost_match: Does pricing info align? (null if no pricing on page)

Return ONLY valid JSON:
{{
  "school_match": true/false,
  "ia_mentioned": true/false,
  "program_match": true/false,
  "cost_match": true/false/null,
  "confidence_score": 1-10,
  "validation_status": "VALIDATED" or "LIKELY_VALID" or "SUSPECT",
  "notes": "1 sentence explanation"
}}"""

# ─── LLM Client ──────────────────────────────────────────────────────────────

def create_client() -> OpenAI:
    if not CLOUDRIFT_API_KEY:
        raise RuntimeError("CLOUDRIFT_API_KEY not set — check your .env file")
    return OpenAI(api_key=CLOUDRIFT_API_KEY, base_url=CLOUDRIFT_BASE_URL)


def call_llm(client: OpenAI, prompt: str) -> dict:
    try:
        resp = client.chat.completions.create(
            model=CLOUDRIFT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
            timeout=LLM_TIMEOUT,
        )
        output = resp.choices[0].message.content or ""
    except Exception as e:
        return {"error": str(e)[:200]}

    m = re.search(r'\{[^{}]*\}', output, re.DOTALL)
    if not m:
        m = re.search(r'\{.*\}', output, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            return {"error": "json_parse_failed", "raw": output[:300]}
    return {"error": "no_json_found", "raw": output[:300]}


# ─── Page Fetching ────────────────────────────────────────────────────────────

def fetch_page(url: str) -> tuple:
    """Returns (status_code, text, error)."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, timeout=HTTP_TIMEOUT, allow_redirects=True, headers=headers)
        if resp.status_code >= 400:
            return resp.status_code, None, f"HTTP {resp.status_code}"
        text = extract_text(resp.text)
        return resp.status_code, text, None
    except requests.exceptions.Timeout:
        return 0, None, "timeout"
    except requests.exceptions.ConnectionError as e:
        return 0, None, f"conn_error: {str(e)[:80]}"
    except Exception as e:
        return 0, None, f"error: {str(e)[:80]}"


def extract_text(html: str) -> str:
    for tag in ["script", "style", "nav", "footer", "header", "noscript"]:
        html = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()

    sentences = text.split(".")
    relevant = []
    for i, s in enumerate(sentences):
        if any(kw in s.lower() for kw in IA_KEYWORDS):
            relevant.extend(sentences[max(0, i-1):min(len(sentences), i+2)])
    if relevant:
        text = ". ".join(dict.fromkeys(relevant))

    return text[:PAGE_TEXT_MAX] + ("... [truncated]" if len(text) > PAGE_TEXT_MAX else "")


# ─── Verification Logic ──────────────────────────────────────────────────────

def verify_school(client: OpenAI, row: dict) -> dict:
    """Verify a single school. Returns dict with v_* fields."""
    url = (row.get("source_url") or "").strip()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # No URL → can't verify
    if not url or url.lower() in ("n/a", "none", ""):
        return {
            "v_status": "NO_URL", "v_score": 0, "v_url_code": 0,
            "v_notes": "No source URL available — needs research",
            "v_at": now,
        }

    # Tier 1: HTTP check
    code, page_text, err = fetch_page(url)
    if not code or code >= 400:
        return {
            "v_status": "URL_BROKEN", "v_score": 0, "v_url_code": code or 0,
            "v_notes": err or f"HTTP {code}",
            "v_at": now,
        }

    if not page_text or len(page_text.strip()) < 50:
        return {
            "v_status": "SUSPECT", "v_score": 1, "v_url_code": code,
            "v_notes": "Page loaded but no useful text",
            "v_at": now,
        }

    # Tier 2: LLM verification
    prompt = VERIFY_PROMPT.format(
        school_name=row.get("school_name", ""),
        city=row.get("city", ""),
        state=row.get("state", ""),
        has_ia=row.get("has_ia", ""),
        ia_program_name=row.get("ia_program_name", ""),
        cost_model=row.get("cost_model", ""),
        price=row.get("price", ""),
        notes=row.get("notes", ""),
        source_url=url,
        page_text=page_text,
    )

    result = call_llm(client, prompt)

    if "error" in result:
        return {
            "v_status": "SUSPECT", "v_score": 0, "v_url_code": code,
            "v_notes": f"LLM error: {result['error'][:100]}",
            "v_at": now,
        }

    return {
        "v_status": result.get("validation_status", "SUSPECT"),
        "v_score": result.get("confidence_score", 0),
        "v_url_code": code,
        "v_notes": result.get("notes", ""),
        "v_at": now,
    }


# ─── Checkpoint I/O ──────────────────────────────────────────────────────────

def load_checkpoint() -> dict:
    """Load checkpoint: school_name (lowered) → full row dict."""
    done = {}
    if os.path.exists(CHECKPOINT_CSV):
        with open(CHECKPOINT_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = row.get("school_name", "").strip().lower()
                if key:
                    done[key] = row
    return done


def append_checkpoint(row: dict):
    """Append a single verified row to the checkpoint file."""
    file_exists = os.path.exists(CHECKPOINT_CSV)
    with open(CHECKPOINT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VERIFY_COLS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def write_final_output(checkpoint: dict, remaining: list):
    """Merge checkpoint results + unverified remaining into one output file."""
    all_rows = list(checkpoint.values()) + remaining
    all_rows.sort(key=lambda r: r.get("school_name", ""))
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VERIFY_COLS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)


# ─── Stats ────────────────────────────────────────────────────────────────────

def print_stats(checkpoint: dict, total: int):
    stats = {}
    for row in checkpoint.values():
        s = row.get("v_status", "UNKNOWN")
        stats[s] = stats.get(s, 0) + 1

    done = len(checkpoint)
    remaining = total - done
    pct = (done / total * 100) if total else 0

    print(f"\n{'=' * 60}")
    print(f"  Silver Verification Progress")
    print(f"{'=' * 60}")
    print(f"  Total schools:  {total}")
    print(f"  Verified:       {done} ({pct:.1f}%)")
    print(f"  Remaining:      {remaining}")
    print(f"{'─' * 60}")
    for status in ["VALIDATED", "LIKELY_VALID", "SUSPECT", "URL_BROKEN", "NO_URL"]:
        icon = {"VALIDATED": "✅", "LIKELY_VALID": "🔵", "SUSPECT": "⚠️ ", "URL_BROKEN": "❌", "NO_URL": "⬜"}.get(status, "❓")
        cnt = stats.get(status, 0)
        print(f"  {icon} {status:15s} {cnt:>5}")
    print(f"{'=' * 60}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Verify SILVER dataset with Cloudrift")
    parser.add_argument("--batch-size", type=int, default=0,
                        help="Max schools to verify this run (0 = all)")
    parser.add_argument("--urls-only", action="store_true",
                        help="Only verify schools that have real source URLs (skip N/A)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without verifying")
    parser.add_argument("--reset", action="store_true",
                        help="Delete checkpoint and start fresh")
    parser.add_argument("--stats", action="store_true",
                        help="Show current progress and exit")
    parser.add_argument("--input", type=str, default=INPUT_CSV,
                        help="Input CSV (default: silver_dataset.csv)")
    args = parser.parse_args()

    # Load input data
    with open(args.input, newline="", encoding="utf-8") as f:
        all_schools = list(csv.DictReader(f))
    total = len(all_schools)

    # Handle --reset
    if args.reset:
        if os.path.exists(CHECKPOINT_CSV):
            os.remove(CHECKPOINT_CSV)
            print("🗑️  Checkpoint deleted. Starting fresh.")
        else:
            print("No checkpoint to delete.")
        return

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Handle --stats
    if args.stats:
        print_stats(checkpoint, total)
        return

    # Determine what needs verification
    to_verify = []
    for row in all_schools:
        key = row["school_name"].strip().lower()
        if key not in checkpoint:
            url = (row.get("source_url") or "").strip()
            has_url = url and url.lower() not in ("n/a", "none", "")
            if args.urls_only and not has_url:
                continue
            to_verify.append(row)

    # Sort: schools with URLs first (they need actual verification)
    def url_sort_key(r):
        u = (r.get("source_url") or "").strip()
        return 0 if u and u.lower() not in ("n/a", "none", "") else 1
    to_verify.sort(key=url_sort_key)

    if args.batch_size > 0:
        to_verify = to_verify[:args.batch_size]

    print(f"{'=' * 60}")
    print(f"  Silver Verification — Cloudrift/Gemma 3 12B")
    print(f"{'=' * 60}")
    print(f"  Total silver schools:  {total}")
    print(f"  Already verified:      {len(checkpoint)}")
    print(f"  To verify this run:    {len(to_verify)}")
    if args.batch_size > 0:
        print(f"  Batch size limit:      {args.batch_size}")
    print(f"{'=' * 60}")

    if not to_verify:
        print("\n✅ All schools already verified!")
        print_stats(checkpoint, total)
        # Write final output
        remaining_rows = [r for r in all_schools if r["school_name"].strip().lower() not in checkpoint]
        write_final_output(checkpoint, remaining_rows)
        print(f"\n💾 Final output: {OUTPUT_CSV}")
        return

    if args.dry_run:
        print(f"\n[DRY RUN] Would verify {len(to_verify)} schools. No changes saved.")
        for r in to_verify[:10]:
            url = r.get("source_url", "N/A")
            print(f"  • {r['school_name']} — URL: {url[:60]}")
        if len(to_verify) > 10:
            print(f"  ... and {len(to_verify) - 10} more")
        return

    # Create LLM client
    client = create_client()

    # Run verification
    session_stats = {}
    session_start = time.time()

    for i, row in enumerate(to_verify, 1):
        if _SHUTDOWN:
            print(f"\n🛑 Graceful shutdown after {i-1} schools.")
            break

        school = row["school_name"]
        url = (row.get("source_url") or "N/A")[:50]
        print(f"\n[{i}/{len(to_verify)}] {school}")
        print(f"  URL: {url}...")

        t0 = time.time()
        result = verify_school(client, row)
        elapsed = time.time() - t0

        status = result["v_status"]
        score = result["v_score"]
        notes = result.get("v_notes", "")

        icon = {"VALIDATED": "✅", "LIKELY_VALID": "🔵", "SUSPECT": "⚠️ ", "URL_BROKEN": "❌", "NO_URL": "⬜"}.get(status, "❓")
        print(f"  {icon} {status} (score: {score}/10, {elapsed:.1f}s)")
        if notes:
            print(f"  📝 {notes[:100]}")

        # Merge result into row and save to checkpoint
        row.update(result)
        append_checkpoint(row)
        checkpoint[school.strip().lower()] = row

        session_stats[status] = session_stats.get(status, 0) + 1

        # ETA calculation
        avg_time = (time.time() - session_start) / i
        remaining = len(to_verify) - i
        eta_min = (remaining * avg_time) / 60
        print(f"  ⏱️  ETA: {eta_min:.0f} min remaining ({avg_time:.1f}s/school avg)")

        if i < len(to_verify) and not _SHUTDOWN:
            time.sleep(DELAY_BETWEEN)

    # Session summary
    elapsed_total = (time.time() - session_start) / 60
    print(f"\n{'=' * 60}")
    print(f"  Session Complete — {elapsed_total:.1f} minutes")
    print(f"{'─' * 60}")
    for status in ["VALIDATED", "LIKELY_VALID", "SUSPECT", "URL_BROKEN", "NO_URL"]:
        cnt = session_stats.get(status, 0)
        if cnt:
            icon = {"VALIDATED": "✅", "LIKELY_VALID": "🔵", "SUSPECT": "⚠️ ", "URL_BROKEN": "❌", "NO_URL": "⬜"}.get(status, "❓")
            print(f"  {icon} {status:15s} {cnt:>5}")
    print(f"{'=' * 60}")

    # Overall progress
    print_stats(checkpoint, total)

    # Write final output if all done
    verified_count = len(checkpoint)
    if verified_count >= total:
        remaining_rows = [r for r in all_schools if r["school_name"].strip().lower() not in checkpoint]
        write_final_output(checkpoint, remaining_rows)
        print(f"\n💾 Final output written: {OUTPUT_CSV}")
    else:
        print(f"\n💡 Run again to continue ({total - verified_count} remaining)")
        print(f"   python scripts/pipeline/verify_silver.py")


if __name__ == "__main__":
    main()
