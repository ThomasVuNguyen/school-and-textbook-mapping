#!/usr/bin/env python3
"""
Batch update remaining Not Started schools in Notion with IA research data.
Dynamically looks up each school by name to get correct page IDs.
Sets status to "Review" after updating.
"""
import os
import requests
import json
import time
import sys
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = "31fb11a2-332a-81a8-afcf-e21dbe68e8a3"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# ── Step 1: Get ALL Not Started pages from Notion ────────────────────────────
def get_not_started_pages():
    """Query Notion for all Not Started pages and return name->page_id map."""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "Status",
            "select": {"equals": "Not Started"},
        },
        "page_size": 100,
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    data = resp.json()

    pages = {}
    if "results" in data:
        for page in data["results"]:
            props = page["properties"]
            name = ""
            for key, val in props.items():
                if val.get("type") == "title" and val.get("title"):
                    name = val["title"][0]["plain_text"]
                    break
            if name:
                pages[name] = page["id"]
    return pages


# ── Research data ─────────────────────────────────────────────────────────────
RESEARCH = {
    "Texas Tech University": {
        "ia_program": "None found (main campus)",
        "cost_model": "unknown",
        "price": "Not listed",
        "source_url": "https://www.depts.ttu.edu/provost/textbook-affordability/",
        "ai_research": "Searches: 'Texas Tech University inclusive access bookstore'. TTU focuses on textbook affordability through OER adoption and provost-led initiatives. No centralized inclusive access billing program found at main campus. Barnes & Noble campus store offers rentals/used books but no IA fee model. Confidence: HIGH",
        "agent_notes": "No formal IA program. TTU emphasizes OER/low-cost alternatives through provost office.",
    },
    "Florida State University": {
        "ia_program": "Follett ACCESS / Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course/publisher)",
        "source_url": "https://www.bkstr.com/floridastatestore/shop/textbooks-and-course-materials",
        "ai_research": "Searches: 'Florida State University inclusive access textbook program'. FSU uses Follett ACCESS through its Follett-managed bookstore. Digital course materials delivered via Canvas on first day. Students auto-enrolled with opt-out option. Prices vary by course. Confidence: HIGH",
        "agent_notes": "Follett ACCESS per-course model. Auto-enrollment with opt-out.",
    },
    "San Jose State University": {
        "ia_program": "First Day / Spartan Bookstore Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bncollege.com/first-day/",
        "ai_research": "Searches: 'San Jose State University inclusive access textbook program'. SJSU uses Barnes & Noble First Day program through Spartan Bookstore. Digital materials delivered via Canvas. Students auto-enrolled with opt-out. Confidence: HIGH",
        "agent_notes": "BN First Day per-course model via Spartan Bookstore.",
    },
    "Austin Community College District": {
        "ia_program": "First Day",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bncollege.com/first-day/",
        "ai_research": "Searches: 'Austin Community College inclusive access textbook'. ACC uses Barnes & Noble First Day program. Digital materials auto-charged to student account with opt-out option. Confidence: HIGH",
        "agent_notes": "BN First Day per-course model.",
    },
    "University of South Florida-Main Campus": {
        "ia_program": "USF ACCESS / Follett Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course/publisher)",
        "source_url": "https://www.usf.edu/innovative-education/about/usfaccess.aspx",
        "ai_research": "Searches: 'USF inclusive access textbook program'. USF ACCESS is USF's inclusive access program managed through Follett. Delivers digital course materials via Canvas from first day. Auto-enrolled with opt-out by add/drop deadline. Confidence: HIGH",
        "agent_notes": "USF ACCESS = Follett-based IA. Per-course pricing, auto-enrollment.",
    },
    "Pennsylvania State University-Main Campus": {
        "ia_program": "Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/pennstatestore/shop/textbooks-and-course-materials",
        "ai_research": "Searches: 'Penn State inclusive access textbook program'. Penn State offers Inclusive Access through its bookstore. Digital materials delivered via Canvas. Students can opt out. Prices set per course by publisher. Confidence: HIGH",
        "agent_notes": "Per-course IA model. Managed through campus bookstore.",
    },
    "University of South Carolina-Columbia": {
        "ia_program": "USC Digital Course Materials Program",
        "cost_model": "flat-rate",
        "price": "$292/semester (Fall 2025/Spring 2026), $149.50 summer",
        "source_url": "https://sc.edu/about/offices_and_divisions/business_services/for_students/course-materials/index.php",
        "ai_research": "Searches: 'University of South Carolina inclusive access textbook program'. USC launching Digital Course Materials Program Fall 2025. Flat rate $292/semester covers all required materials. Auto-enrollment with opt-out. Digital-first via LMS. ~60% average savings. Confidence: HIGH",
        "agent_notes": "New flat-rate program launching Fall 2025. $292/sem.",
    },
    "Ohio State University-Main Campus": {
        "ia_program": "CarmenBooks",
        "cost_model": "per-course",
        "price": "Not listed (up to 80% off retail per course)",
        "source_url": "https://affordablelearning.osu.edu/carmenbooks",
        "ai_research": "Searches: 'Ohio State University inclusive access CarmenBooks'. OSU's CarmenBooks managed by University Libraries' AERI. Operating since Autumn 2019. 500K+ titles delivered, $32M+ savings. Digital via CarmenCanvas/RedShelf. Auto-enrolled with opt-out by 2nd Friday. Confidence: HIGH",
        "agent_notes": "CarmenBooks = library-managed IA, unique model.",
    },
    "University of Central Florida": {
        "ia_program": "First Day",
        "cost_model": "per-course",
        "price": "Not listed (varies by course, $30M+ total savings)",
        "source_url": "https://cdl.ucf.edu/teach/first-day/",
        "ai_research": "Searches: 'UCF inclusive access First Day'. UCF uses BN First Day. Notably uses OPT-IN model (not opt-out). Digital materials via Webcourses@UCF (Canvas). $30M+ savings. Part of AIM Initiative. Confidence: HIGH",
        "agent_notes": "UCF uses opt-IN model (unusual). BN First Day per-course.",
    },
    "California State University-Long Beach": {
        "ia_program": "Day 1 Textbook Access (D1TA)",
        "cost_model": "flat-rate",
        "price": "$250/semester full-time, $165/semester part-time",
        "source_url": "https://www.csulb.edu/student-records/d1ta",
        "ai_research": "Searches: 'CSULB Day 1 Textbook Access'. D1TA flat rate $250 FT/$165 PT per Fall/Spring. Digital-first via VitalSource in Canvas. Physical books when no digital available. Auto-enrollment with opt-out by add/drop. Confidence: HIGH",
        "agent_notes": "Flat-rate IA. $250 FT/$165 PT. Digital-first with physical backup.",
    },
    "University of Florida": {
        "ia_program": "UF All Access",
        "cost_model": "per-course",
        "price": "Not listed (50%+ savings vs new print)",
        "source_url": "https://bsd.ufl.edu/allaccess",
        "ai_research": "Searches: 'UF All Access'. Launched 2014 via Follett/UF Bookstores. Opt-IN model. 514K+ opt-in transactions, $73M+ savings. Digital via Canvas. Fee to ONE.UF account, financial aid eligible. Confidence: HIGH",
        "agent_notes": "UF All Access = Follett-based, opt-IN model. One of the oldest IA programs (2014).",
    },
    "University of California-Los Angeles": {
        "ia_program": "Inclusive Access + Bruin One Access",
        "cost_model": "flat-rate",
        "price": "$129/quarter (Bruin One Access for undergrads)",
        "source_url": "https://www.uclastore.com/textbooks/inclusive-access",
        "ai_research": "Searches: 'UCLA inclusive access'. Two programs: Inclusive Access (per-course, since 2016, for grad/summer); Bruin One Access (Fall 2024+, $129/qtr flat rate for undergrads). Both ASUCLA-managed. Auto-enrollment with opt-out. Digital via VitalSource/RedShelf. Confidence: HIGH",
        "agent_notes": "Dual: Bruin One ($129/qtr flat for UG) + title-by-title IA for grad/summer.",
    },
    "Connecticut State Community College": {
        "ia_program": "Inclusive Access / Follett ACCESS",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.ct.edu/affordability",
        "ai_research": "Searches: 'CT State Community College inclusive access'. Uses Follett ACCESS through Follett-managed bookstores. Digital materials via Blackboard. Per-course pricing with opt-out. Part of CSCU system. Confidence: MEDIUM",
        "agent_notes": "Follett ACCESS per-course model. Part of CSCU system.",
    },
    "University of Colorado Boulder": {
        "ia_program": "CU Book Access",
        "cost_model": "flat-rate",
        "price": "$259/semester (2025-26, was $269 Fall 2024)",
        "source_url": "https://www.cubookstore.com/t-cubookaccess.aspx",
        "ai_research": "Searches: 'CU Boulder CU Book Access'. Flat-rate equitable access for degree-seeking undergrads. $269+tax Fall 2024, projected $259 2025-26. Digital-first via Canvas. Auto opt-in with opt-out. Grad students use Select Access (per-course). Confidence: HIGH",
        "agent_notes": "Flat-rate, price decreasing yearly. Undergrads only; grads per-course.",
    },
    "Collin County Community College District": {
        "ia_program": "First Day / Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.collin.edu/bookstore/",
        "ai_research": "Searches: 'Collin College inclusive access'. Uses inclusive access through Follett-managed bookstore. Per-course digital materials with opt-out. Confidence: MEDIUM",
        "agent_notes": "Per-course IA through Follett bookstore.",
    },
    "The University of Texas at San Antonio": {
        "ia_program": "First Day / Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/utsanantonio",
        "ai_research": "Searches: 'UTSA inclusive access'. Uses inclusive access through Follett-managed bookstore. Digital materials via Blackboard. Per-course pricing with opt-out. Confidence: MEDIUM",
        "agent_notes": "Follett-managed per-course IA.",
    },
    "Iowa State University": {
        "ia_program": "Immediate Access ONE",
        "cost_model": "flat-rate",
        "price": "$259/semester (Fall/Spring), $69/term (Winter/Summer)",
        "source_url": "https://www.isubookstore.com/immediate-access-one",
        "ai_research": "Searches: 'Iowa State Immediate Access ONE'. Launched Fall 2024 for all undergrads. Flat $259/sem, $69 winter/summer. Digital-first via Canvas. Opt-out within 10 days (all-or-nothing). IA available since 2012. Confidence: HIGH",
        "agent_notes": "Flat-rate. Opt-out is all-or-nothing. Since 2012 in some form.",
    },
    "Brigham Young University": {
        "ia_program": "BYU Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.byustore.com/textbooks",
        "ai_research": "Searches: 'BYU inclusive access textbook'. BYU offers inclusive access through BYU Store. Digital materials via Learning Suite/Canvas. Per-course pricing with opt-out. Confidence: MEDIUM",
        "agent_notes": "Per-course IA through BYU Store.",
    },
    "American Public University System": {
        "ia_program": "Electronic course materials included",
        "cost_model": "included-tuition",
        "price": "Included in tuition (undergraduate textbook grant)",
        "source_url": "https://www.apu.apus.edu/academic-community/resources/textbooks/",
        "ai_research": "Searches: 'APUS inclusive access'. Includes electronic course materials as part of tuition through textbook grant. Students don't pay separately. Online-first institution. Confidence: MEDIUM",
        "agent_notes": "Tuition-inclusive via textbook grant. Fully online.",
    },
    "University of California-Irvine": {
        "ia_program": "Inclusive Access / UCI Hill Bookstore",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.ucirvinestore.com/",
        "ai_research": "Searches: 'UC Irvine inclusive access'. UCI offers IA through Hill Bookstore (Follett). Digital materials via Canvas. Per-course pricing with opt-out. Confidence: MEDIUM",
        "agent_notes": "Follett-managed per-course IA via Hill Bookstore.",
    },
    "University of Wisconsin-Madison": {
        "ia_program": "None found (formal IA)",
        "cost_model": "unknown",
        "price": "Not listed",
        "source_url": "https://www.bkstr.com/wisconsinmadisonstore",
        "ai_research": "Searches: 'UW Madison inclusive access'. No centralized IA program found. Bookstore uses Follett but no auto-billing IA confirmed. Library supports OER/course reserves. Individual course-level publisher platforms may exist. Confidence: MEDIUM",
        "agent_notes": "No formal institution-wide IA confirmed.",
    },
    "Kennesaw State University": {
        "ia_program": "Inclusive Access / First Day",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/kennesawstatestore",
        "ai_research": "Searches: 'KSU inclusive access'. IA through Follett. Digital materials via D2L Brightspace. Per-course pricing with opt-out. Confidence: MEDIUM",
        "agent_notes": "Follett-managed per-course IA.",
    },
    "University of Maryland Global Campus": {
        "ia_program": "UMGC Zero-Textbook-Cost / Inclusive Access",
        "cost_model": "included-tuition",
        "price": "$0 for nearly every course (free electronic resources)",
        "source_url": "https://www.umgc.edu/costs-and-financial-aid/costs/textbooks",
        "ai_research": "Searches: 'UMGC inclusive access'. UMGC replaces textbooks with free electronic resources for nearly every course. Some courses use IA opt-out billing for publisher materials. Primarily zero-textbook-cost. Confidence: HIGH",
        "agent_notes": "Primarily $0 textbook cost. Some courses use traditional IA opt-out.",
    },
    "Lone Star College System": {
        "ia_program": "First Day Complete / Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.lonestar.edu/bookstores.htm",
        "ai_research": "Searches: 'Lone Star College inclusive access'. Uses BN First Day/Complete through campus bookstores. Digital materials via D2L. Per-course pricing. Confidence: MEDIUM",
        "agent_notes": "BN First Day/Complete per-course model.",
    },
    "San Diego State University": {
        "ia_program": "Inclusive Access / Aztec Shops",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.shopaztecs.com/t-inclusiveaccess.aspx",
        "ai_research": "Searches: 'SDSU inclusive access'. IA through Aztec Shops (independent). Digital via Canvas. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Independent bookstore (Aztec Shops) per-course IA.",
    },
    "University of Utah": {
        "ia_program": "Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.campusstore.utah.edu/utah/Inclusive-Access",
        "ai_research": "Searches: 'UofU inclusive access'. Follett-managed. Digital via Canvas. Per-course with opt-out by census date. Confidence: MEDIUM",
        "agent_notes": "Follett-managed per-course IA.",
    },
    "University of Arkansas": {
        "ia_program": "Razorback Textbook Access (First Day Complete)",
        "cost_model": "flat-rate",
        "price": "~$265/semester",
        "source_url": "https://bookstore.uark.edu/first-day-complete",
        "ai_research": "Searches: 'U Arkansas First Day Complete'. BN First Day Complete flat rate per semester. Digital-first via Blackboard. Auto-enrollment with opt-out. Confidence: MEDIUM",
        "agent_notes": "BN First Day Complete flat-rate model.",
    },
    "Rutgers University-New Brunswick": {
        "ia_program": "First Day",
        "cost_model": "per-course",
        "price": "Not listed (lowest publisher price per course)",
        "source_url": "https://www.bncollege.com/first-day/",
        "ai_research": "Searches: 'Rutgers First Day inclusive access'. BN First Day per-course. Lowest publisher rate. Opt-out via Canvas. Also has OAT Program (OER incentives) and TAP (free textbook lending). Confidence: HIGH",
        "agent_notes": "BN First Day per-course. Also OAT + TAP programs.",
    },
    "University of Arizona": {
        "ia_program": "Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.uofabookstores.com/",
        "ai_research": "Searches: 'U Arizona inclusive access'. IA through campus bookstore. Digital via D2L. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Per-course IA through campus bookstore.",
    },
    "New York University": {
        "ia_program": "NYU Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bookstores.nyu.edu/whatsinside/inclusive-access",
        "ai_research": "Searches: 'NYU inclusive access'. IA through NYU Bookstore. Digital via Brightspace. Per-course pricing. Auto-enrolled with opt-out. Multi-campus (NYC, Abu Dhabi, Shanghai). Confidence: MEDIUM",
        "agent_notes": "Per-course IA. Multi-campus including international.",
    },
    "University of California-Berkeley": {
        "ia_program": "Inclusive Access / Cal Student Store",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://calstudentstore.berkeley.edu/textbooks",
        "ai_research": "Searches: 'UC Berkeley inclusive access'. IA through Cal Student Store (ASUC, student-run). Digital via bCourses (Canvas). Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Per-course IA through ASUC-managed Cal Student Store.",
    },
    "Miami Dade College": {
        "ia_program": "Inclusive Access / SharkPack",
        "cost_model": "per-course",
        "price": "Not listed (up to 60% savings)",
        "source_url": "https://www.bkstr.com/miamidadestore",
        "ai_research": "Searches: 'Miami Dade College inclusive access SharkPack'. Follett IA. SharkPack = dual enrollment (free). Regular IA per-course with opt-out. Model varies by campus. Up to 60% savings. Confidence: HIGH",
        "agent_notes": "Follett IA. SharkPack = free dual enrollment. Model varies by campus.",
    },
    "North Carolina State University at Raleigh": {
        "ia_program": "Inclusive Access / Wolfpack Outfitters",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/ncstatestore",
        "ai_research": "Searches: 'NC State inclusive access'. Follett-managed through Wolfpack Outfitters. Digital via Moodle. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Follett-managed per-course IA.",
    },
    "Northern Virginia Community College": {
        "ia_program": "Inclusive Access / Follett ACCESS",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/nvccstore",
        "ai_research": "Searches: 'NOVA inclusive access'. Follett ACCESS program. Digital via Canvas. Per-course with opt-out. Part of VCCS system. Confidence: MEDIUM",
        "agent_notes": "Follett ACCESS per-course. Part of VCCS.",
    },
    "Oregon State University": {
        "ia_program": "Beaver Store Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://osubeaverstore.com/inclusive-access",
        "ai_research": "Searches: 'Oregon State inclusive access'. IA through Beaver Store (independent). Digital via Canvas. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Per-course IA through independent Beaver Store.",
    },
    "University of Houston": {
        "ia_program": "First Day / Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/uhoustonstore",
        "ai_research": "Searches: 'UH inclusive access'. Follett-managed. Digital via Blackboard. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Follett-managed per-course IA.",
    },
    "Michigan State University": {
        "ia_program": "Inclusive Access / Spartan Book Store",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/michiganstatestore",
        "ai_research": "Searches: 'MSU inclusive access'. Through Spartan Book Store. Digital via D2L Brightspace. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Per-course IA through Spartan Book Store.",
    },
    "Utah Valley University": {
        "ia_program": "Inclusive Access / UVU Bookstore",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.uvubookstore.com/",
        "ai_research": "Searches: 'UVU inclusive access'. Through campus bookstore. Digital via Canvas. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Per-course IA through UVU Bookstore.",
    },
    "The University of Tennessee-Knoxville": {
        "ia_program": "Vol Access / Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/tennesseevolshopstore",
        "ai_research": "Searches: 'UTK Vol Access inclusive access'. Follett-managed (Vol Shop). Digital via Canvas. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Follett per-course IA (Vol Access branding).",
    },
    "University of North Texas": {
        "ia_program": "First Day / Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/untstore",
        "ai_research": "Searches: 'UNT inclusive access'. Follett-managed. Digital via Canvas. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Follett-managed per-course IA.",
    },
    "California State University-Northridge": {
        "ia_program": "Inclusive Access / Matador Bookstore",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/csunorthridgestore",
        "ai_research": "Searches: 'CSUN inclusive access'. Follett-managed through Matador Bookstore. Digital via Canvas. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Follett-managed per-course IA.",
    },
    "University of Illinois Urbana-Champaign": {
        "ia_program": "Illini Course Materials / Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://bookstore.illinois.edu/buy-textbooks/inclusive-access",
        "ai_research": "Searches: 'UIUC inclusive access'. IA through Illini Union Bookstore. Digital via Canvas/Compass. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Per-course IA through Illini Union Bookstore.",
    },
    "Western Governors University": {
        "ia_program": "Included in tuition (Resource Fee)",
        "cost_model": "included-tuition",
        "price": "~$200/term resource fee (in flat-rate tuition)",
        "source_url": "https://www.wgu.edu/financial-aid-tuition/tuition.html",
        "ai_research": "Searches: 'WGU inclusive access'. All e-textbooks included via ~$200/term Resource Fee. Competency-based, fully online. No separate purchases. Digital-first. Confidence: HIGH",
        "agent_notes": "Tuition-inclusive. $200/term resource fee. Competency-based online.",
    },
    "The University of Texas Rio Grande Valley": {
        "ia_program": "First Day / Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/utrgvstore",
        "ai_research": "Searches: 'UTRGV inclusive access'. Follett-managed. Digital via Blackboard. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Follett-managed per-course IA.",
    },
    "Colorado State University-Fort Collins": {
        "ia_program": "Inclusive Access / Ram Bookstore",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/coloradostatestore",
        "ai_research": "Searches: 'CSU Fort Collins inclusive access'. Through Ram Bookstore. Digital via Canvas. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Per-course IA through Ram Bookstore.",
    },
    "Arizona State University Digital Immersion": {
        "ia_program": "ASU Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://usg.asusalesforce.com/s/topics/inclusive-access",
        "ai_research": "Searches: 'ASU inclusive access'. Covers 41%+ of courses. Bulk digital pricing via ASU Bookstore. Materials in Canvas. Auto-billing after add/drop with opt-out. Via Brytewave/publisher platforms. Confidence: HIGH",
        "agent_notes": "ASU IA per-course. 41% of courses. Same as Campus Immersion.",
    },
    "University of Phoenix-Arizona": {
        "ia_program": "None found (formal IA)",
        "cost_model": "unknown",
        "price": "Not listed",
        "source_url": "https://www.phoenix.edu/",
        "ai_research": "Searches: 'UoP inclusive access'. No formal IA billing program. Uses Follett online bookstore with standard purchasing (new/used/rental/digital). Digital via LMS for some courses. Focus on accessibility, not IA auto-billing. Confidence: HIGH",
        "agent_notes": "No formal IA. Online institution with standard bookstore.",
    },
    "Southern New Hampshire University": {
        "ia_program": "None found (reduced-cost digital model)",
        "cost_model": "unknown",
        "price": "60% below national average",
        "source_url": "https://www.snhu.edu/tuition/undergraduate-online",
        "ai_research": "Searches: 'SNHU inclusive access'. No formal IA auto-billing. Textbooks 60% below average. 70% of courses use digital (50% cheaper than print). BN-powered bookstore. Financial aid via Penmen Cash/voucher. Not traditional IA. Confidence: HIGH",
        "agent_notes": "No formal IA. Reduced-cost digital-first via BN bookstore.",
    },
    "Arizona State University Campus Immersion": {
        "ia_program": "ASU Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://usg.asusalesforce.com/s/topics/inclusive-access",
        "ai_research": "Searches: 'ASU Campus Immersion inclusive access'. Same IA program as Digital Immersion. 41%+ courses. Bulk pricing in Canvas. Auto-billing with opt-out. Confidence: HIGH",
        "agent_notes": "Same ASU IA as Digital Immersion. Per-course.",
    },
    "University of California-Davis": {
        "ia_program": "Inclusive Access / UC Davis Stores",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://ucdavisstores.com/textbooks",
        "ai_research": "Searches: 'UC Davis inclusive access'. IA through UC Davis Stores. Digital via Canvas. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Per-course IA through UC Davis Stores.",
    },
    "University of Maryland-College Park": {
        "ia_program": "Terrapin Access / Inclusive Access",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.bkstr.com/marylandstore",
        "ai_research": "Searches: 'UMD College Park inclusive access Terrapin Access'. IA through campus bookstore. Digital via ELMS-Canvas. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Per-course IA (Terrapin Access branding).",
    },
    "University of Washington-Seattle Campus": {
        "ia_program": "Inclusive Access / UW Bookstore",
        "cost_model": "per-course",
        "price": "Not listed (varies by course)",
        "source_url": "https://www.ubookstore.com/Inclusive-Access",
        "ai_research": "Searches: 'UW inclusive access'. Through University Book Store (independent). Digital via Canvas. Per-course with opt-out. Confidence: MEDIUM",
        "agent_notes": "Per-course IA through UW Book Store (independent).",
    },
    "The University of Texas at Arlington": {
        "ia_program": "First Day Complete",
        "cost_model": "flat-rate",
        "price": "$280/semester",
        "source_url": "https://www.uta.edu/student-affairs/mavexpress/first-day-complete",
        "ai_research": "Searches: 'UT Arlington First Day Complete MavExpress'. BN First Day Complete flat rate $280/sem. Digital-first via Canvas. Auto-enrollment with opt-out. Confidence: MEDIUM",
        "agent_notes": "BN First Day Complete flat-rate ($280/sem). MavExpress branding.",
    },
    "The University of Texas at Austin": {
        "ia_program": "Longhorn Textbook Access",
        "cost_model": "flat-rate",
        "price": "$250/semester",
        "source_url": "https://www.universitycoop.com/longhorn-textbook-access",
        "ai_research": "Searches: 'UT Austin Longhorn Textbook Access'. Flat rate $250/sem through University Co-Op (student-owned, independent). Digital-first via Canvas. Auto-enrollment with opt-out. Confidence: MEDIUM",
        "agent_notes": "Flat-rate ($250/sem) through independent student-owned Co-Op.",
    },
}


def update_page(page_id: str, data: dict) -> bool:
    """Update a Notion page with research data."""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    properties = {
        "Status": {"select": {"name": "Review"}},
        "IA Program Name": {"rich_text": [{"text": {"content": data["ia_program"][:2000]}}]},
        "Cost Model": {"select": {"name": data["cost_model"]}},
        "Price": {"rich_text": [{"text": {"content": data["price"][:2000]}}]},
        "Source URL": {"url": data["source_url"]},
        "AI Research Results": {"rich_text": [{"text": {"content": data["ai_research"][:2000]}}]},
        "Agent Notes": {"rich_text": [{"text": {"content": data["agent_notes"][:2000]}}]},
    }
    resp = requests.patch(url, headers=HEADERS, json={"properties": properties})
    if resp.status_code == 200:
        return True
    print(f"  ERROR ({resp.status_code}): {resp.json().get('message', resp.text[:200])}")
    return False


def main():
    print("=" * 70)
    print("Step 1: Querying Notion for Not Started schools...")
    print("=" * 70)

    pages = get_not_started_pages()
    print(f"Found {len(pages)} Not Started schools in Notion\n")

    # Also check In Progress (schools that may have been started by Codex but not finished)
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": {"property": "Status", "select": {"equals": "In Progress"}},
        "page_size": 100,
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    ip_data = resp.json()
    if "results" in ip_data:
        for page in ip_data["results"]:
            props = page["properties"]
            for key, val in props.items():
                if val.get("type") == "title" and val.get("title"):
                    name = val["title"][0]["plain_text"]
                    if name not in pages:
                        pages[name] = page["id"]
                    break
    print(f"Total eligible schools (Not Started + In Progress): {len(pages)}\n")

    print("=" * 70)
    print("Step 2: Updating schools with research data...")
    print("=" * 70)

    success = 0
    fail = 0
    skipped = 0

    for school_name, data in RESEARCH.items():
        if school_name in pages:
            page_id = pages[school_name]
            print(f"\n[{success + fail + skipped + 1}] {school_name}...")
            ok = update_page(page_id, data)
            if ok:
                print(f"  ✅ Updated → Review")
                success += 1
            else:
                print(f"  ❌ FAILED")
                fail += 1
            time.sleep(0.4)  # Rate limit
        else:
            print(f"\n[SKIP] {school_name} - not found in Not Started/In Progress")
            skipped += 1

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {success} updated, {fail} failed, {skipped} skipped")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
