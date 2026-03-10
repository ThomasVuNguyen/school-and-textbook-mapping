#!/usr/bin/env python3
"""
build_roster.py — Build a master CSV roster of U.S. colleges and universities
from the College Scorecard API.

Usage:
    export COLLEGE_SCORECARD_API_KEY=your_key
    python build_roster.py

Outputs:
    us_colleges_master.csv
    us_colleges_master_state_counts.csv
"""

import csv
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests

# ── Configuration ───────────────────────────────────────────────────────────

API_KEY = os.environ.get("COLLEGE_SCORECARD_API_KEY", "")
BASE_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"
PER_PAGE = 100
SLEEP_BETWEEN_PAGES = 0.4  # seconds, to respect rate limits

# Fields to request from the API
API_FIELDS = ",".join([
    "id",
    "ope6_id",
    "school.name",
    "school.city",
    "school.state",
    "school.state_fips",
    "school.ownership",
    "school.degrees_awarded.predominant",
    "school.institutional_characteristics.level",
    "school.school_url",
    "school.zip",
    "location.lat",
    "location.lon",
])

# ── Reference tables ───────────────────────────────────────────────────────

VALID_USPS_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI",
    "WY",
    # Territories
    "AS", "GU", "MH", "FM", "MP", "PW", "PR", "VI",
}

STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12",
    "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18",
    "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23",
    "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
    "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44",
    "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
    "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55",
    "WY": "56",
    "AS": "60", "GU": "66", "MH": "68", "FM": "64", "MP": "69",
    "PW": "70", "PR": "72", "VI": "78",
}

OWNERSHIP_MAP = {1: "public", 2: "private_nonprofit", 3: "private_forprofit"}

# school.institutional_characteristics.level
LEVEL_MAP = {
    1: "4-year",
    2: "2-year",
    3: "less_than_2_year",
}

# school.degrees_awarded.predominant
PREDOMINANT_MAP = {
    0: "not_classified",
    1: "certificate",
    2: "associate",
    3: "bachelor",
    4: "graduate_only",
}


def derive_sector(control: str, level: str) -> str:
    """Combine control and level into a normalized sector tag."""
    if control == "public" and level == "2-year":
        return "public_cc"
    if control == "public" and level == "4-year":
        return "public_4y"
    if control == "private_nonprofit" and level == "2-year":
        return "private_nonprofit_2y"
    if control == "private_nonprofit" and level == "4-year":
        return "private_nonprofit_4y"
    if control == "private_forprofit" and level == "2-year":
        return "private_forprofit_2y"
    if control == "private_forprofit" and level == "4-year":
        return "private_forprofit_4y"
    return "other"


def normalize_url(raw: str | None) -> str:
    """Best-effort normalization of school URL."""
    if not raw or str(raw).strip().lower() in ("", "null", "none", "nan"):
        return ""
    url = str(raw).strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def safe_str(val) -> str:
    """Convert value to string, handling None/NaN."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val)


# ── API Pull ───────────────────────────────────────────────────────────────

def fetch_all_schools(api_key: str) -> list[dict]:
    """Paginate through the entire College Scorecard API and return raw rows."""
    all_results = []
    page = 0
    total_expected = None

    while True:
        params = {
            "api_key": api_key,
            "fields": API_FIELDS,
            "per_page": PER_PAGE,
            "page": page,
        }

        for attempt in range(5):
            try:
                resp = requests.get(BASE_URL, params=params, timeout=30)
                if resp.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    print(f"  ⏳ Rate-limited on page {page}, backing off {wait}s …")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                break
            except requests.exceptions.RequestException as exc:
                if attempt == 4:
                    print(f"  ❌ Failed on page {page} after 5 retries: {exc}")
                    raise
                time.sleep(2 ** attempt)
        else:
            break

        data = resp.json()
        metadata = data.get("metadata", {})
        results = data.get("results", [])

        if total_expected is None:
            total_expected = metadata.get("total", "?")
            print(f"📊 API reports {total_expected} total institutions")

        if not results:
            break

        all_results.extend(results)
        fetched = len(all_results)
        print(f"  ✅ Page {page:>3d} — {len(results):>3d} results (cumulative: {fetched})")

        page += 1
        time.sleep(SLEEP_BETWEEN_PAGES)

    print(f"\n📥 Fetched {len(all_results)} raw records\n")
    return all_results


# ── Transform ──────────────────────────────────────────────────────────────

def transform(raw_rows: list[dict], pulled_at: str) -> pd.DataFrame:
    """Map raw API results into the target schema.

    NOTE: The College Scorecard API returns FLAT dot-notation keys,
    e.g. "school.name", "school.city", "location.lat" — NOT nested dicts.
    """
    records = []

    for row in raw_rows:
        unitid = safe_str(row.get("id"))
        ope6 = safe_str(row.get("ope6_id"))

        state = safe_str(row.get("school.state"))
        state_fips_raw = row.get("school.state_fips")

        # Derive statefp — prefer API value, fallback to lookup
        if state_fips_raw is not None and str(state_fips_raw).strip() not in ("", "None"):
            statefp = str(int(float(str(state_fips_raw)))).zfill(2)
        else:
            statefp = STATE_FIPS.get(state, "")

        ownership_code = row.get("school.ownership")
        control = OWNERSHIP_MAP.get(ownership_code, "other")

        level_code = row.get("school.institutional_characteristics.level")
        level = LEVEL_MAP.get(level_code, "other")

        predominant_code = row.get("school.degrees_awarded.predominant")

        # Refine level using predominant degree if the level field is missing/other
        if level == "other" and predominant_code in (3, 4):
            level = "4-year"
        elif level == "other" and predominant_code in (1, 2):
            level = "2-year"

        sector = derive_sector(control, level)

        url = normalize_url(row.get("school.school_url"))
        zipcode = safe_str(row.get("school.zip"))
        lat = row.get("location.lat")
        lon = row.get("location.lon")

        notes_parts = []
        if state and state not in VALID_USPS_STATES:
            notes_parts.append(f"unknown_state={state}")
        if not unitid:
            notes_parts.append("missing_unitid")
        if ownership_code not in (1, 2, 3):
            notes_parts.append(f"unknown_ownership={ownership_code}")

        records.append({
            "unitid": unitid,
            "school_name": safe_str(row.get("school.name")),
            "state": state,
            "statefp": statefp,
            "city": safe_str(row.get("school.city")),
            "sector": sector,
            "control": control,
            "level": level,
            "official_website": url,
            "opeid6": ope6,
            "system_affiliation": "",
            "source": "college_scorecard",
            "pulled_at": pulled_at,
            "latitude": safe_str(lat) if lat is not None else "",
            "longitude": safe_str(lon) if lon is not None else "",
            "zip": zipcode,
            "notes": "; ".join(notes_parts) if notes_parts else "",
        })

    df = pd.DataFrame(records)
    return df


# ── Quality Checks ────────────────────────────────────────────────────────

def quality_checks(df: pd.DataFrame) -> pd.DataFrame:
    """Run quality checks and deduplicate."""

    # 1. Deduplicate by unitid
    before = len(df)
    df = df.drop_duplicates(subset="unitid", keep="first").copy()
    dupes_removed = before - len(df)
    if dupes_removed:
        print(f"⚠️  Removed {dupes_removed} duplicate unitid rows")
    else:
        print("✅ No duplicate unitid values found")

    # 2. Validate state codes
    invalid_states = df[
        (df["state"] != "") & (~df["state"].isin(VALID_USPS_STATES))
    ]
    if len(invalid_states) > 0:
        print(f"⚠️  {len(invalid_states)} rows with invalid state codes:")
        for _, r in invalid_states.head(10).iterrows():
            print(f"     unitid={r['unitid']}  state={r['state']}  name={r['school_name']}")
    else:
        print("✅ All state codes are valid USPS abbreviations")

    # 3. Validate statefp
    bad_fips = df[
        (df["statefp"] != "") & (df["statefp"].str.len() != 2)
    ]
    if len(bad_fips) > 0:
        print(f"⚠️  {len(bad_fips)} rows with non-2-digit statefp")
    else:
        print("✅ All statefp values are 2-digit strings")

    return df


# ── Export ─────────────────────────────────────────────────────────────────

def export_master(df: pd.DataFrame, path: str):
    """Export master CSV with leading zeros preserved."""
    # Ensure string types for zero-padded columns
    for col in ("unitid", "opeid6", "statefp", "zip"):
        df[col] = df[col].astype(str)

    column_order = [
        "unitid", "school_name", "state", "statefp", "city",
        "sector", "control", "level", "official_website", "opeid6",
        "system_affiliation", "source", "pulled_at",
        "latitude", "longitude", "zip", "notes",
    ]
    df = df[column_order]
    df.to_csv(path, index=False, quoting=csv.QUOTE_ALL)
    print(f"\n📁 Saved {path} ({len(df)} rows)")


def export_state_counts(df: pd.DataFrame, path: str):
    """Export state-level counts."""
    counts = (
        df.groupby(["state", "statefp"])
        .size()
        .reset_index(name="school_count")
        .sort_values("state")
    )
    counts.to_csv(path, index=False, quoting=csv.QUOTE_ALL)
    print(f"📁 Saved {path} ({len(counts)} rows)")


# ── Summary ────────────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame):
    """Print a short console summary."""
    print("\n" + "=" * 60)
    print("  US COLLEGES MASTER ROSTER — SUMMARY")
    print("=" * 60)
    print(f"  Total rows:              {len(df):,}")
    print(f"  Unique states/territories: {df['state'].nunique()}")
    print(f"  Rows missing website:    {(df['official_website'] == '').sum():,}")
    print(f"  Rows missing opeid6:     {((df['opeid6'] == '') | (df['opeid6'] == 'nan')).sum():,}")
    print()
    print("  Rows by sector:")
    sector_counts = df["sector"].value_counts().sort_index()
    for sector, count in sector_counts.items():
        print(f"    {sector:<30s} {count:>6,}")
    print()
    print("  Rows by control:")
    control_counts = df["control"].value_counts().sort_index()
    for ctrl, count in control_counts.items():
        print(f"    {ctrl:<30s} {count:>6,}")
    print()
    print("  Rows by level:")
    level_counts = df["level"].value_counts().sort_index()
    for lvl, count in level_counts.items():
        print(f"    {lvl:<30s} {count:>6,}")
    print("=" * 60)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    if not API_KEY:
        print("❌ Set COLLEGE_SCORECARD_API_KEY environment variable first.")
        sys.exit(1)

    pulled_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"🕐 Pull timestamp: {pulled_at}\n")

    # 1. Fetch
    raw = fetch_all_schools(API_KEY)

    # 2. Transform
    df = transform(raw, pulled_at)

    # 3. Quality checks
    df = quality_checks(df)

    # 4. Export
    out_dir = os.path.dirname(os.path.abspath(__file__))
    master_path = os.path.join(out_dir, "us_colleges_master.csv")
    state_path = os.path.join(out_dir, "us_colleges_master_state_counts.csv")

    export_master(df, master_path)
    export_state_counts(df, state_path)

    # 5. Summary
    print_summary(df)

    # 6. Suspicious rows report
    suspicious = df[df["notes"] != ""]
    if len(suspicious) > 0:
        print(f"\n⚠️  {len(suspicious)} rows have notes/flags:")
        for _, r in suspicious.head(20).iterrows():
            print(f"   unitid={r['unitid']}  {r['school_name']}  — {r['notes']}")
    else:
        print("\n✅ No suspicious rows flagged")


if __name__ == "__main__":
    main()
