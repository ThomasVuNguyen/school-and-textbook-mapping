#!/usr/bin/env python3
"""
IA Research Validation Checker
───────────────────────────────
Validates research results using a 2-tier approach:
  Tier 1 — HTTP check: is the source URL reachable?
  Tier 2 — LLM check:  does page content corroborate the research data?

Validation statuses:
  VALIDATED    → URL works + LLM confirms data matches page content
  LIKELY_VALID → URL works + LLM says probably correct but not 100%
  SUSPECT      → something doesn't line up, needs manual review
  URL_BROKEN   → URL returns 4xx/5xx or connection error, skip LLM

Usage:
  source .venv/bin/activate
  python validate_results.py                        # validate all unvalidated
  python validate_results.py --batch-size 20        # validate 20 at a time
  python validate_results.py --recheck-suspects     # re-validate SUSPECT rows
  python validate_results.py --recheck-broken       # re-validate URL_BROKEN rows
  python validate_results.py --dry-run              # preview without saving
"""

import csv
import json
import os
import re
import time
import argparse
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from openai import OpenAI

# ─── Environment & Config ────────────────────────────────────────────────────

load_dotenv()

CLOUDRIFT_API_KEY = os.getenv("CLOUDRIFT_API_KEY")
CLOUDRIFT_BASE_URL = os.getenv("CLOUDRIFT_BASE_URL", "https://llm-gateway.cloudrift.ai/v1")
CLOUDRIFT_MODEL = os.getenv("CLOUDRIFT_MODEL", "google/gemma-3-12b-it")

RESULTS_CSV = "data/raw/research_results.csv"
VALIDATED_CSV = "data/validated/research_results_validated.csv"

DELAY_BETWEEN_CALLS = 1        # seconds between API calls (much faster than CLI)
HTTP_TIMEOUT = 10               # seconds for URL check
LLM_TIMEOUT = 30                # seconds for API call
PAGE_TEXT_MAX_CHARS = 2000      # max chars sent to LLM

VALIDATION_FIELDS = [
    "validation_status",        # VALIDATED / LIKELY_VALID / SUSPECT / URL_BROKEN
    "validation_score",         # 1-10 confidence from LLM
    "validated_at",             # ISO timestamp
    "validation_notes",         # human-readable explanation
    "url_status_code",          # HTTP status code from URL check
]

# Keywords used to extract relevant text sections from page HTML
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
- IA Program: {ia_program}
- Cost Model: {cost_model}
- Price: {price}
- Summary: {summary}
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


# ─── API Client ──────────────────────────────────────────────────────────────

def create_llm_client() -> OpenAI:
    """Create OpenAI-compatible client for Cloudrift."""
    if not CLOUDRIFT_API_KEY:
        raise RuntimeError("CLOUDRIFT_API_KEY not set — check your .env file")
    return OpenAI(api_key=CLOUDRIFT_API_KEY, base_url=CLOUDRIFT_BASE_URL)


def call_llm(client: OpenAI, prompt: str) -> dict:
    """Send a prompt to the Cloudrift LLM and parse the JSON response."""
    try:
        completion = client.chat.completions.create(
            model=CLOUDRIFT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,            # low temp for consistent validation
            max_tokens=300,
            timeout=LLM_TIMEOUT,
        )
        output = completion.choices[0].message.content or ""
    except Exception as e:
        return {"error": str(e)[:200]}

    # Extract JSON from response
    json_match = re.search(r'\{[^{}]*\}', output, re.DOTALL)
    if not json_match:
        json_match = re.search(r'\{.*\}', output, re.DOTALL)

    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return {"error": "json_parse_failed", "raw": output[:300]}

    return {"error": "no_json_found", "raw": output[:300]}


# ─── Page Fetching & Text Extraction ─────────────────────────────────────────

def fetch_page_text(url: str) -> tuple[int, str | None, str | None]:
    """
    Fetch a URL and extract relevant text content.
    Returns (status_code, extracted_text, error_string).
    """
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

        text = _extract_relevant_text(resp.text)
        return resp.status_code, text, None

    except requests.exceptions.Timeout:
        return 0, None, "Connection timeout"
    except requests.exceptions.ConnectionError as e:
        return 0, None, f"Connection error: {str(e)[:100]}"
    except Exception as e:
        return 0, None, f"Error: {str(e)[:100]}"


def _extract_relevant_text(html: str) -> str:
    """
    Strip HTML junk, then extract only sentences containing IA-related keywords.
    Falls back to the full (truncated) text if no keyword matches are found.
    """
    # Remove non-content blocks
    for tag in ["script", "style", "nav", "footer", "header", "noscript"]:
        html = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Strip remaining tags → plain text
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()

    # Find sentences that contain relevant keywords (± 1 sentence of context)
    sentences = text.split(".")
    relevant = []
    for i, sentence in enumerate(sentences):
        if any(kw in sentence.lower() for kw in IA_KEYWORDS):
            start = max(0, i - 1)
            end = min(len(sentences), i + 2)
            relevant.extend(sentences[start:end])

    if relevant:
        text = ". ".join(dict.fromkeys(relevant))  # dedupe, preserve order

    # Hard cap
    if len(text) > PAGE_TEXT_MAX_CHARS:
        text = text[:PAGE_TEXT_MAX_CHARS] + "... [truncated]"

    return text


# ─── Validation Logic ────────────────────────────────────────────────────────

def validate_row(client: OpenAI, row: dict) -> dict:
    """
    Run validation on a single research result.
    Tier 1: check URL reachability.
    Tier 2: if URL works, send page text + research data to LLM for verification.
    """
    url = row["source_url"]
    school = row["school_name"]
    state = row["state"]
    city = row.get("city", "")

    # ── Tier 1: URL reachability ──────────────────────────────────────────
    status_code, page_text, http_error = fetch_page_text(url)
    url_ok = status_code and status_code < 400

    if not url_ok:
        return {
            "validation_status": "URL_BROKEN",
            "validation_score": 0,
            "url_status_code": status_code or 0,
            "validation_notes": f"URL returned {http_error or 'error'} — needs regeneration",
        }

    if not page_text or len(page_text.strip()) < 50:
        return {
            "validation_status": "SUSPECT",
            "validation_score": 1,
            "url_status_code": status_code,
            "validation_notes": "Page loaded but contained no useful text",
        }

    # ── Tier 2: LLM verification ─────────────────────────────────────────
    prompt = VERIFY_PROMPT.format(
        school_name=school,
        city=city,
        state=state,
        ia_program=row.get("ia_program", ""),
        cost_model=row.get("cost_model", ""),
        price=row.get("price", ""),
        summary=row.get("summary", ""),
        source_url=url,
        page_text=page_text,
    )

    llm_result = call_llm(client, prompt)

    if "error" in llm_result:
        return {
            "validation_status": "SUSPECT",
            "validation_score": 0,
            "url_status_code": status_code,
            "validation_notes": f"LLM error: {llm_result['error']}",
        }

    return {
        "validation_status": llm_result.get("validation_status", "SUSPECT"),
        "validation_score": llm_result.get("confidence_score", 0),
        "url_status_code": status_code,
        "validation_notes": llm_result.get("notes", ""),
    }


# ─── CSV I/O ─────────────────────────────────────────────────────────────────

def load_results(path: str) -> list[dict]:
    """Load research results from CSV."""
    with open(path, "r") as f:
        return list(csv.DictReader(f))


def save_results(rows: list[dict], path: str):
    """Save validated results to CSV, preserving all columns."""
    if not rows:
        return
    all_fields = list(rows[0].keys())
    for vf in VALIDATION_FIELDS:
        if vf not in all_fields:
            all_fields.append(vf)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate IA Research Results")
    parser.add_argument("--batch-size", type=int, default=0, help="Max schools to validate (0 = all)")
    parser.add_argument("--recheck-suspects", action="store_true", help="Re-validate SUSPECT entries")
    parser.add_argument("--recheck-broken", action="store_true", help="Re-validate URL_BROKEN entries")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--input", type=str, default=RESULTS_CSV, help="Input CSV")
    parser.add_argument("--output", type=str, default=VALIDATED_CSV, help="Output CSV")
    args = parser.parse_args()

    # Init
    client = create_llm_client()
    rows = load_results(args.input)

    print("=" * 70)
    print("IA Research Validation Checker  (Cloudrift Gemma 3 12B)")
    print(f"Total results: {len(rows)}")
    print("=" * 70)

    # Determine which rows need validation
    to_validate = []
    already_valid = 0

    for i, row in enumerate(rows):
        status = row.get("validation_status", "")
        if status in ("VALIDATED", "LIKELY_VALID") and not args.recheck_suspects:
            already_valid += 1
            continue
        if status == "SUSPECT" and not args.recheck_suspects:
            continue
        if status == "URL_BROKEN" and not args.recheck_broken:
            continue
        if status == "":
            to_validate.append(i)
            continue
        to_validate.append(i)

    if args.batch_size > 0:
        to_validate = to_validate[:args.batch_size]

    print(f"Already validated: {already_valid}")
    print(f"To validate this run: {len(to_validate)}")
    if args.dry_run:
        print("[DRY RUN] No changes will be saved")
    print("=" * 70)

    if not to_validate:
        print("Nothing to validate!")
        return

    # Run validation
    stats = {"VALIDATED": 0, "LIKELY_VALID": 0, "SUSPECT": 0, "URL_BROKEN": 0}

    for count, idx in enumerate(to_validate, 1):
        row = rows[idx]
        school = row["school_name"]
        print(f"\n[{count}/{len(to_validate)}] Validating: {school}...")

        t0 = time.time()
        result = validate_row(client, row)
        elapsed = time.time() - t0

        status = result["validation_status"]
        score = result["validation_score"]
        notes = result.get("validation_notes", "")

        # Update the row in-place
        row["validation_status"] = status
        row["validation_score"] = score
        row["validated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        row["validation_notes"] = notes
        row["url_status_code"] = result.get("url_status_code", "")

        icon = {"VALIDATED": "✅", "LIKELY_VALID": "🔵", "SUSPECT": "⚠️", "URL_BROKEN": "❌"}.get(status, "❓")
        print(f"  {icon} {status} (score: {score}/10, {elapsed:.1f}s)")
        if notes:
            print(f"  📝 {notes[:120]}")

        stats[status] = stats.get(status, 0) + 1

        # Rate limit between API calls (only if next row needs LLM)
        if count < len(to_validate):
            time.sleep(DELAY_BETWEEN_CALLS)

    # Save
    if not args.dry_run:
        save_results(rows, args.output)
        print(f"\n💾 Saved to: {args.output}")

    # Summary
    print(f"\n{'=' * 70}")
    print("VALIDATION SUMMARY")
    print(f"  ✅ VALIDATED:    {stats['VALIDATED']}")
    print(f"  🔵 LIKELY_VALID: {stats['LIKELY_VALID']}")
    print(f"  ⚠️  SUSPECT:     {stats['SUSPECT']}")
    print(f"  ❌ URL_BROKEN:   {stats['URL_BROKEN']}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
