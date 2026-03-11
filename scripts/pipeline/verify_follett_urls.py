#!/usr/bin/env python3
"""
verify_follett_urls.py — Batch-verify Follett-partnered schools by checking
their OFFICIAL WEBSITE for bookstore / inclusive access pages.

Strategy:
  For each Follett-partnered school, use their official_website to check
  common bookstore/IA URL patterns like:
    {official_website}/bookstore
    bookstore.{domain}
    {official_website}/inclusive-access
    {official_website}/textbooks

  If we get a 200 on any of these, we have a verified source URL.

Resumable via checkpoint file.
"""

import csv, re, os, sys, json, time, signal, argparse
import asyncio, aiohttp
from pathlib import Path
from urllib.parse import urlparse

# ── Paths ──────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent.parent
INPUT_CSV = BASE / "data" / "raw" / "access_code_research_results.csv"
CHECKPOINT = BASE / "data" / "validated" / "follett_url_checkpoint.csv"

# ── URL pattern generation ─────────────────────────────────────────────
def generate_candidate_urls(official_website: str) -> list[str]:
    """Generate candidate bookstore/IA URLs from a school's official website."""
    if not official_website or official_website.strip() in ('', 'N/A', 'none'):
        return []

    url = official_website.strip().rstrip('/')
    if not url.startswith('http'):
        url = 'https://' + url

    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split('/')[0]
    domain = domain.replace('www.', '')
    base = f"https://www.{domain}"

    candidates = [
        # Bookstore paths
        f"{base}/bookstore",
        f"{base}/books",
        f"{base}/textbooks",
        # Inclusive Access specific paths
        f"{base}/inclusive-access",
        f"{base}/inclusiveaccess",
        f"{base}/day-one-access",
        f"{base}/first-day",
        # Subdomain patterns
        f"https://bookstore.{domain}",
        # Common university bookstore patterns
        f"{base}/campus-life/bookstore",
        f"{base}/current-students/bookstore",
        f"{base}/student-life/bookstore",
        f"{base}/services/bookstore",
    ]
    return candidates


# ── HTTP checking ──────────────────────────────────────────────────────
async def check_url(session: aiohttp.ClientSession, url: str,
                    timeout: int = 8) -> tuple[str, int]:
    """Check if a URL exists. Returns (final_url, status_code)."""
    try:
        async with session.head(url, timeout=aiohttp.ClientTimeout(total=timeout),
                                allow_redirects=True, ssl=False) as resp:
            return (str(resp.url), resp.status)
    except Exception:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout),
                                   allow_redirects=True, ssl=False) as resp:
                return (str(resp.url), resp.status)
        except Exception:
            return (url, 0)


async def find_school_url(session: aiohttp.ClientSession,
                          official_website: str) -> tuple[str, int, str]:
    """Try candidate URLs to find a working bookstore/IA page.
    Returns (found_url, status, match_type)."""
    candidates = generate_candidate_urls(official_website)
    if not candidates:
        return ("", 0, "no_website")

    # Check all candidates in parallel
    tasks = [check_url(session, url) for url in candidates]
    results = await asyncio.gather(*tasks)

    # Return the first working URL
    for (final_url, status), original in zip(results, candidates):
        if 200 <= status < 400:
            # Determine match type
            if 'inclusive' in original.lower() or 'first-day' in original.lower():
                match_type = "ia_page"
            elif 'bookstore' in original.lower() or 'books' in original.lower():
                match_type = "bookstore_page"
            else:
                match_type = "other"
            return (final_url, status, match_type)

    # If none worked, at least check if the main website is up
    main_url, main_status = await check_url(session, official_website.strip())
    if 200 <= main_status < 400:
        return (str(main_url), main_status, "main_site_only")

    return ("", 0, "all_failed")


# ── Main ───────────────────────────────────────────────────────────────
STOP = False
def handle_signal(sig, frame):
    global STOP
    print("\n⚠️  Ctrl+C received — finishing current batch, then saving...")
    STOP = True

signal.signal(signal.SIGINT, handle_signal)


def load_checkpoint() -> dict:
    """Load already-checked schools from checkpoint."""
    done = {}
    if CHECKPOINT.exists():
        with open(CHECKPOINT) as f:
            for row in csv.DictReader(f):
                done[row["school_name"].strip().lower()] = row
    return done


async def main(args):
    global STOP

    # Load input data
    with open(INPUT_CSV) as f:
        all_rows = list(csv.DictReader(f))

    # Filter to Follett schools
    follett = [r for r in all_rows if 'follett' in r.get('bookstore_partner', '').lower()]
    print(f"Total Follett schools: {len(follett)}")

    # Load checkpoint
    checkpoint = load_checkpoint()
    print(f"Already checked: {len(checkpoint)}")

    # Filter to unchecked
    to_check = [r for r in follett if r["school_name"].strip().lower() not in checkpoint]

    if args.batch_size > 0:
        to_check = to_check[:args.batch_size]

    print(f"To check this run: {len(to_check)}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would check {len(to_check)} schools.")
        has_web = sum(1 for r in to_check if r.get('official_website','').strip() not in ('','N/A','none'))
        no_web = len(to_check) - has_web
        print(f"  With official website: {has_web}")
        print(f"  Missing website: {no_web}")
        for r in to_check[:5]:
            urls = generate_candidate_urls(r.get("official_website", ""))
            print(f"  {r['school_name']} → {len(urls)} candidate URLs")
            for u in urls[:3]:
                print(f"    {u}")
        return

    if not to_check:
        print("Nothing to check!")
        show_stats(checkpoint, len(follett))
        return

    # Ensure checkpoint file exists with header
    if not CHECKPOINT.exists():
        CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
        with open(CHECKPOINT, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["school_name", "verified_url", "http_status",
                           "match_type", "official_website", "checked_at"])

    # Process in batches of 10 (each school checks ~12 URLs = 120 parallel)
    BATCH = 10
    counts = {"ia_page": 0, "bookstore_page": 0, "main_site_only": 0,
              "other": 0, "no_website": 0, "all_failed": 0}
    start = time.time()

    conn = aiohttp.TCPConnector(limit=50, ssl=False)
    async with aiohttp.ClientSession(connector=conn, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }) as session:

        for i in range(0, len(to_check), BATCH):
            if STOP:
                break

            batch = to_check[i:i+BATCH]
            tasks = [
                find_school_url(session, r.get("official_website", ""))
                for r in batch
            ]
            results = await asyncio.gather(*tasks)

            # Save results
            with open(CHECKPOINT, 'a', newline='') as f:
                writer = csv.writer(f)
                for row, (url, status, match_type) in zip(batch, results):
                    writer.writerow([
                        row["school_name"],
                        url,
                        status,
                        match_type,
                        row.get("official_website", ""),
                        time.strftime("%Y-%m-%d")
                    ])
                    counts[match_type] = counts.get(match_type, 0) + 1

            elapsed = time.time() - start
            done_count = sum(counts.values())
            rate = done_count / elapsed if elapsed > 0 else 0
            remaining = len(to_check) - done_count
            eta = remaining / rate / 60 if rate > 0 else 0
            found = counts["ia_page"] + counts["bookstore_page"]

            print(f"  [{done_count}/{len(to_check)}] "
                  f"📚 {counts['bookstore_page']} bookstore, "
                  f"🎯 {counts['ia_page']} IA page, "
                  f"🌐 {counts['main_site_only']} main only, "
                  f"❌ {counts['all_failed']+counts['no_website']} failed "
                  f"({rate:.1f}/sec, ETA: {eta:.1f} min)")

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  Done in {elapsed/60:.1f} minutes")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        icon = {"ia_page": "🎯", "bookstore_page": "📚", "main_site_only": "🌐",
                "other": "🔵", "no_website": "⬜", "all_failed": "❌"}.get(k, "?")
        print(f"  {icon} {k}: {v}")
    print(f"{'='*60}")

    checkpoint = load_checkpoint()
    show_stats(checkpoint, len(follett))


def show_stats(checkpoint: dict, total: int):
    counts = {}
    for v in checkpoint.values():
        mt = v.get("match_type", "unknown")
        counts[mt] = counts.get(mt, 0) + 1

    found = counts.get("ia_page", 0) + counts.get("bookstore_page", 0)
    print(f"\n{'='*60}")
    print(f"  Follett URL Verification Progress")
    print(f"{'='*60}")
    print(f"  Total Follett schools: {total}")
    print(f"  Checked:     {len(checkpoint)} ({100*len(checkpoint)/total:.1f}%)")
    print(f"  📚 Bookstore found: {counts.get('bookstore_page', 0)}")
    print(f"  🎯 IA page found:   {counts.get('ia_page', 0)}")
    print(f"  🌐 Main site only:  {counts.get('main_site_only', 0)}")
    print(f"  ❌ Failed:           {counts.get('all_failed', 0)}")
    print(f"  ⬜ No website:       {counts.get('no_website', 0)}")
    print(f"  Remaining:   {total - len(checkpoint)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Follett school URLs")
    parser.add_argument("--batch-size", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    if args.reset:
        if CHECKPOINT.exists():
            CHECKPOINT.unlink()
            print("🗑️  Checkpoint deleted.")
        sys.exit(0)

    if args.stats:
        with open(INPUT_CSV) as f:
            total = sum(1 for r in csv.DictReader(f)
                       if 'follett' in r.get('bookstore_partner','').lower())
        show_stats(load_checkpoint(), total)
        sys.exit(0)

    asyncio.run(main(args))
