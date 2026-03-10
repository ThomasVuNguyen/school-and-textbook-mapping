#!/usr/bin/env python3
"""
consolidate_data.py — Merge all IA research data sources into a single
master dataset, classify each school's data quality, and split into:

  1. data/validated/gold_dataset.csv    — HIGH confidence, locked
  2. data/validated/silver_dataset.csv  — MEDIUM confidence, usable but could improve
  3. data/raw/needs_research.csv        — LOW/NO data, needs (re-)generation

Data sources (priority order, highest first):
  A. data/validated/verified_dataset.csv        (304 manually curated entries)
  B. Notion scripts: hardcoded research from Perplexity, Codex, Gemini (~70)
  C. data/raw/research_results.csv              (61 Gemini CLI results)
  D. data/raw/access_code_research_results.csv  (6,424 bulk-researched)

Master roster: data/reference/us_colleges_master.csv (6,429 schools)

Usage:
    python scripts/pipeline/consolidate_data.py [--dry-run]
"""
import csv
import os
import sys
import argparse
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = os.path.join(os.path.dirname(__file__), "..", "..")
MASTER_ROSTER  = os.path.join(BASE, "data/reference/us_colleges_master.csv")
VERIFIED       = os.path.join(BASE, "data/validated/verified_dataset.csv")
GEMINI_CLI     = os.path.join(BASE, "data/raw/research_results.csv")
BULK_RESEARCH  = os.path.join(BASE, "data/raw/access_code_research_results.csv")

OUT_GOLD       = os.path.join(BASE, "data/validated/gold_dataset.csv")
OUT_SILVER     = os.path.join(BASE, "data/validated/silver_dataset.csv")
OUT_NEEDS      = os.path.join(BASE, "data/raw/needs_research.csv")
OUT_MASTER     = os.path.join(BASE, "data/validated/master_consolidated.csv")

# ── Hardcoded Notion data (from sync_perplexity_batch, update_all_remaining,
#    update_codex_batch2) — extracted inline so we don't depend on running
#    those scripts. Only the school names and key fields. ─────────────────────
# We import these from the actual script files dynamically.

# ── Quality classification ────────────────────────────────────────────────────
VALID_COST_MODELS = {
    "per-course", "flat-rate", "flat-rate-semester", "flat-rate-credit",
    "per-credit-hour", "included-tuition", "unknown"
}

OUTPUT_COLUMNS = [
    "unitid", "school_name", "state", "city",
    "has_ia", "ia_program_name", "cost_model", "price",
    "source_url", "confidence", "notes",
    "data_source", "quality_tier", "consolidated_at"
]


def load_master_roster():
    """Load the 6,429-school master roster as the denominator."""
    schools = {}
    with open(MASTER_ROSTER, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = row["school_name"].strip().lower()
            schools[key] = {
                "unitid":      row["unitid"],
                "school_name": row["school_name"].strip(),
                "state":       row["state"],
                "city":        row.get("city", ""),
            }
    return schools


def load_verified_dataset():
    """Load the 304-row verified dataset (highest priority)."""
    data = {}
    if not os.path.exists(VERIFIED):
        return data
    with open(VERIFIED, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = row["school_name"].strip().lower()
            has_ia = row.get("has_ia_program", "").strip().lower()
            data[key] = {
                "has_ia":          "yes" if has_ia == "yes" else "no" if has_ia == "no" else "unclear",
                "ia_program_name": row.get("ia_program_name", "").strip(),
                "cost_model":      row.get("ia_cost_model", "").strip(),
                "price":           row.get("ia_price", "").strip(),
                "source_url":      row.get("source_url", "").strip(),
                "confidence":      row.get("confidence", "").strip(),
                "notes":           row.get("notes", "").strip(),
                "data_source":     "verified_dataset",
            }
    return data


def load_gemini_cli():
    """Load 61-row Gemini CLI research results."""
    data = {}
    if not os.path.exists(GEMINI_CLI):
        return data
    with open(GEMINI_CLI, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = row["school_name"].strip().lower()
            ia_prog = row.get("ia_program", "").strip()
            has_ia = "no" if ia_prog.lower() in ("none", "none found", "n/a", "") else "yes"
            data[key] = {
                "has_ia":          has_ia,
                "ia_program_name": ia_prog,
                "cost_model":      row.get("cost_model", "").strip(),
                "price":           row.get("price", "").strip(),
                "source_url":      row.get("source_url", "").strip(),
                "confidence":      row.get("confidence", "").strip(),
                "notes":           row.get("summary", "").strip(),
                "data_source":     "gemini_cli",
            }
    return data


def load_bulk_research():
    """Load the 6,424-row bulk research dataset."""
    data = {}
    if not os.path.exists(BULK_RESEARCH):
        return data
    with open(BULK_RESEARCH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = row["school_name"].strip().lower()
            has_ia_raw = row.get("has_inclusive_access", "").strip().lower()
            if has_ia_raw in ("yes", "true"):
                has_ia = "yes"
            elif has_ia_raw in ("no", "false"):
                has_ia = "no"
            else:
                has_ia = "unclear"

            data[key] = {
                "has_ia":          has_ia,
                "ia_program_name": row.get("program_name", "").strip(),
                "cost_model":      row.get("cost_model", "").strip(),
                "price":           "",  # bulk research doesn't have explicit price
                "source_url":      row.get("source_urls", "").strip(),
                "confidence":      "",
                "notes":           row.get("notes", "").strip(),
                "data_source":     "bulk_research",
            }
    return data


def load_notion_scripts():
    """
    Extract hardcoded school data from the Notion sync scripts.
    These are high-quality, human-reviewed Perplexity/Codex/Gemini results.
    """
    data = {}
    scripts_dir = os.path.join(BASE, "scripts", "notion")

    # Parse sync_perplexity_batch.py SCHOOLS list
    try:
        perplexity_file = os.path.join(scripts_dir, "sync_perplexity_batch.py")
        if os.path.exists(perplexity_file):
            ns = {}
            exec(open(perplexity_file).read().split("def curl_api")[0], ns)
            for school in ns.get("SCHOOLS", []):
                key = school["name"].strip().lower()
                ia_prog = school.get("ia_program_name", "")
                has_ia = "no" if "none" in ia_prog.lower() else "yes"
                data[key] = {
                    "has_ia":          has_ia,
                    "ia_program_name": ia_prog,
                    "cost_model":      school.get("cost_model", ""),
                    "price":           school.get("price", ""),
                    "source_url":      school.get("source_url", ""),
                    "confidence":      "HIGH" if "HIGH" in school.get("ai_results", "") else "MEDIUM",
                    "notes":           school.get("notes", ""),
                    "data_source":     "notion_perplexity",
                }
    except Exception as e:
        print(f"  ⚠ Could not parse sync_perplexity_batch.py: {e}")

    # Parse update_all_remaining.py RESEARCH dict
    try:
        remaining_file = os.path.join(scripts_dir, "update_all_remaining.py")
        if os.path.exists(remaining_file):
            content = open(remaining_file).read()
            # Extract just the RESEARCH dict
            start = content.find("RESEARCH = {")
            if start != -1:
                end = content.find("\ndef update_page")
                if end == -1:
                    end = content.find("\n\ndef ")
                chunk = content[start:end]
                ns = {}
                exec(chunk, ns)
                for name, info in ns.get("RESEARCH", {}).items():
                    key = name.strip().lower()
                    ia_prog = info.get("ia_program", "")
                    has_ia = "no" if "none" in ia_prog.lower() else "yes"
                    data[key] = {
                        "has_ia":          has_ia,
                        "ia_program_name": ia_prog,
                        "cost_model":      info.get("cost_model", ""),
                        "price":           info.get("price", ""),
                        "source_url":      info.get("source_url", ""),
                        "confidence":      "HIGH" if "HIGH" in info.get("ai_research", "") else "MEDIUM",
                        "notes":           info.get("agent_notes", ""),
                        "data_source":     "notion_gemini_codex",
                    }
    except Exception as e:
        print(f"  ⚠ Could not parse update_all_remaining.py: {e}")

    # Parse update_codex_batch2.py SCHOOLS list
    try:
        codex_file = os.path.join(scripts_dir, "update_codex_batch2.py")
        if os.path.exists(codex_file):
            content = open(codex_file).read()
            start = content.find("SCHOOLS = [")
            end = content.find("\n]", start) + 2
            chunk = content[start:end]
            ns = {}
            exec(chunk, ns)
            for school in ns.get("SCHOOLS", []):
                key = school["name"].strip().lower()
                ia_prog = school.get("ia_program", "")
                has_ia = "no" if "none" in ia_prog.lower() else "yes"
                data[key] = {
                    "has_ia":          has_ia,
                    "ia_program_name": ia_prog,
                    "cost_model":      school.get("cost_model", ""),
                    "price":           school.get("price", ""),
                    "source_url":      school.get("source_url", ""),
                    "confidence":      "HIGH" if "HIGH" in school.get("ai_results", "") else "MEDIUM",
                    "notes":           school.get("agent_notes", ""),
                    "data_source":     "notion_codex",
                }
    except Exception as e:
        print(f"  ⚠ Could not parse update_codex_batch2.py: {e}")

    return data


def classify_quality(record):
    """
    Assign quality tier based on data completeness and source.

    GOLD   = has_ia is clear + program name + source URL + HIGH confidence
    SILVER = has_ia is clear + some details but incomplete
    BRONZE = any data but low quality / unclear
    NONE   = no data at all
    """
    has_ia = record.get("has_ia", "")
    prog = record.get("ia_program_name", "")
    url = record.get("source_url", "")
    conf = record.get("confidence", "").upper()
    source = record.get("data_source", "")
    cost = record.get("cost_model", "")

    # Schools confirmed as "no IA" with a source are still GOLD
    if has_ia == "no" and url and source in ("verified_dataset", "notion_perplexity", "notion_gemini_codex", "notion_codex"):
        return "GOLD"

    if has_ia == "yes":
        # GOLD: clear program name + source URL + HIGH confidence or from verified dataset
        if prog and prog.lower() not in ("n/a", "", "unknown") and url:
            if source == "verified_dataset" or conf == "HIGH":
                return "GOLD"
            if cost and cost.lower() != "unknown":
                return "SILVER"
            return "SILVER"
        # Has IA flag but missing details
        return "SILVER" if url else "BRONZE"

    if has_ia == "no":
        # Confirmed no IA — good data
        if url or source in ("bulk_research",):
            return "SILVER"
        return "SILVER"

    # unclear / no data
    if has_ia == "unclear":
        return "BRONZE"

    return "NONE"


def main():
    parser = argparse.ArgumentParser(description="Consolidate all IA research data")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing files")
    args = parser.parse_args()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print("=" * 70)
    print("  IA Research Data Consolidation")
    print("=" * 70)

    # Step 1: Load master roster
    print("\n📋 Loading master roster...")
    roster = load_master_roster()
    print(f"   {len(roster)} schools")

    # Step 2: Load all data sources (priority: highest first)
    print("\n📦 Loading data sources...")

    src_verified = load_verified_dataset()
    print(f"   A. verified_dataset:     {len(src_verified)} schools")

    src_notion = load_notion_scripts()
    print(f"   B. Notion scripts:       {len(src_notion)} schools")

    src_gemini = load_gemini_cli()
    print(f"   C. Gemini CLI:           {len(src_gemini)} schools")

    src_bulk = load_bulk_research()
    print(f"   D. bulk research:        {len(src_bulk)} schools")

    # Step 3: Merge — highest priority source wins
    print("\n🔀 Merging (higher priority overwrites lower)...")
    merged = {}

    # Start with blank entries for every school in the roster
    for key, info in roster.items():
        merged[key] = {
            **info,
            "has_ia": "", "ia_program_name": "", "cost_model": "",
            "price": "", "source_url": "", "confidence": "",
            "notes": "", "data_source": "none",
        }

    # Layer D (lowest priority): bulk research
    for key, rec in src_bulk.items():
        if key in merged:
            merged[key].update(rec)

    # Layer C: Gemini CLI
    for key, rec in src_gemini.items():
        if key in merged:
            merged[key].update(rec)

    # Layer B: Notion scripts (Perplexity, Codex, Gemini)
    for key, rec in src_notion.items():
        if key in merged:
            merged[key].update(rec)

    # Layer A (highest priority): verified dataset
    for key, rec in src_verified.items():
        if key in merged:
            merged[key].update(rec)

    # Step 4: Classify quality
    print("\n📊 Classifying quality tiers...")
    gold = []
    silver = []
    needs = []

    for key, rec in merged.items():
        tier = classify_quality(rec)
        rec["quality_tier"] = tier
        rec["consolidated_at"] = now

        if tier == "GOLD":
            gold.append(rec)
        elif tier in ("SILVER",):
            silver.append(rec)
        else:  # BRONZE or NONE
            needs.append(rec)

    print(f"\n   🥇 GOLD   (locked, high confidence): {len(gold)}")
    print(f"   🥈 SILVER (usable, could improve):   {len(silver)}")
    print(f"   🔄 NEEDS RESEARCH (low/no data):     {len(needs)}")
    print(f"   ── Total: {len(gold) + len(silver) + len(needs)}")

    # Step 5: Source attribution breakdown
    source_counts = {}
    for rec in merged.values():
        src = rec.get("data_source", "none")
        source_counts[src] = source_counts.get(src, 0) + 1
    print("\n📈 Data source coverage:")
    for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"   {src:25s} {cnt:>5}")

    # IA breakdown
    ia_yes = sum(1 for r in merged.values() if r.get("has_ia") == "yes")
    ia_no = sum(1 for r in merged.values() if r.get("has_ia") == "no")
    ia_unclear = sum(1 for r in merged.values() if r.get("has_ia") == "unclear")
    ia_none = sum(1 for r in merged.values() if r.get("has_ia") == "")
    print(f"\n📊 IA program breakdown:")
    print(f"   has IA:    {ia_yes}")
    print(f"   no IA:     {ia_no}")
    print(f"   unclear:   {ia_unclear}")
    print(f"   no data:   {ia_none}")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return

    # Step 6: Write output files
    print("\n💾 Writing output files...")

    def write_csv(path, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for r in sorted(rows, key=lambda x: x.get("school_name", "")):
                writer.writerow(r)
        print(f"   ✅ {os.path.basename(path)}: {len(rows)} rows")

    write_csv(OUT_GOLD, gold)
    write_csv(OUT_SILVER, silver)
    write_csv(OUT_NEEDS, needs)
    write_csv(OUT_MASTER, list(merged.values()))

    print(f"\n{'=' * 70}")
    print(f"  CONSOLIDATION COMPLETE")
    print(f"  Gold:   {OUT_GOLD}")
    print(f"  Silver: {OUT_SILVER}")
    print(f"  Needs:  {OUT_NEEDS}")
    print(f"  Master: {OUT_MASTER}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
