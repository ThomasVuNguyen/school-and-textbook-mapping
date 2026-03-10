#!/usr/bin/env python3
"""
sync_perplexity_batch.py — Push Perplexity's research results into the Notion Kanban board.
Uses curl subprocess to avoid Python SSL hangs.
"""
import subprocess, json, time, os
from dotenv import load_dotenv

load_dotenv()

DB_ID = "31fb11a2-332a-81a8-afcf-e21dbe68e8a3"
TOKEN = os.getenv("NOTION_TOKEN")

# ── All 12 schools from Perplexity ──
SCHOOLS = [
    {
        "name": "Auburn University",
        "ia_program_name": "AU All Access",
        "cost_model": "per-course",
        "price": "Not listed (publisher-negotiated per course; no public pricing table)",
        "source_url": "https://www.aubookstore.com/all-access",
        "ai_results": "Searched: \"Auburn University inclusive access textbook\", \"Auburn University AU All Access\", \"Auburn University All Access opt-out instructions\". Found Auburn University Bookstore's official \"AU All Access\" page. All Access is the bookstore's inclusive access program that converts physical course materials into digital content delivered through Canvas on the first day of class. Materials available at no cost through add/drop period (~first two weeks), after which All Access charge appears on the student e-bill if not opted out. Students auto-opted in for participating courses; may opt out via Canvas link up to 15th class day. Prices negotiated with publishers for lowest cost but no public dollar amount. Confidence: HIGH on existence, branding, opt-out rules, per-course model; MEDIUM on pricing.",
        "notes": "AU All Access is Auburn's branded IA program (not Follett ACCESS or First Day Complete), operated by campus bookstore via Canvas and RedShelf/VitalSource. Students opted in by default, must use Canvas opt-out tool by 15th class day. Pricing described as negotiated \"lowest price\" without listing exact fees. Program active 2025-26."
    },
    {
        "name": "George Mason University",
        "ia_program_name": "First Day™",
        "cost_model": "per-course",
        "price": "Not listed (course-specific charge; no public pricing table)",
        "source_url": "https://studentaccounts.gmu.edu/course-material-information/",
        "ai_results": "Searched: \"George Mason University inclusive access textbook\", \"GMU First Day inclusive access\", \"gmu.bncollege First Day FAQ\". GMU Student Accounts page states bookstore's First Day Program is an inclusive access model delivering publisher digital content within Canvas from day one, letting students pay for course materials alongside tuition and fees. BNC First Day FAQS confirms cost of course materials added as additional course charge with opt-out tool in LMS. Neither page publishes per-course dollar amount. Confidence: HIGH on program name (First Day), IA nature, per-course billing; LOW on specific pricing.",
        "notes": "GMU uses Barnes & Noble College First Day inclusive access. Digital materials auto-provisioned in Canvas, billed as course materials charge on student account. Opt-out via Course Materials link in LMS. Pricing course-specific and negotiated."
    },
    {
        "name": "Indiana University-Bloomington",
        "ia_program_name": "IU eTexts",
        "cost_model": "per-course",
        "price": "Not listed (publisher-negotiated eText fee per course; no public rate table)",
        "source_url": "https://iu.pressbooks.pub/iuetexts101/chapter/how-the-iu-etext-program-works/",
        "ai_results": "Searched: \"Indiana University Bloomington inclusive access eText bursar charge\", \"IU eTexts bursar bill Canvas\". IU's official guide explains university negotiates contracts with publishers for digital textbooks at significantly reduced prices. Faculty opt courses into IU eTexts, students charged eText license fee via Bursar's Office. Bursar posts charges to student accounts, handles add/drop adjustments. Students can opt out per federal rules. IU bulletin confirms students \"will be charged the eText fee on their bursar bill\" with day-one Canvas access. No dollar-cost table published. Confidence: HIGH on IA program with per-course bursar fees; LOW-MEDIUM on precise pricing.",
        "notes": "IU eTexts is a mature, institution-run IA program under IU's own branding (not vendor-branded). Charges appear as eText fees on bursar bill per participating course. Materials delivered in Canvas from day one. Students can opt out per federal regulations, default is opt-in billing."
    },
    {
        "name": "Tarrant County College District",
        "ia_program_name": "TCC Plus (Powered by First Day™)",
        "cost_model": "per-course",
        "price": "Varies by course (e.g. FREN-1411 $63.33 vs $135.30 standard); no single standard fee",
        "source_url": "https://www.tccd.edu/services/campus-resources/bookstores/inclusive-access/tcc-plus-faq/",
        "ai_results": "Searched: \"Tarrant County College TCC Plus inclusive access fee\", \"TCC Plus Powered by First Day\". TCC's official FAQ defines TCC Plus (Powered by First Day) as program providing discounted digital textbooks with cost included in class cost. Students pay for TCC Plus materials when paying for classes, shown as \"course materials charge\" covered by financial aid. Prices ~50% less than printed texts. Sample table shows per-course prices (e.g. FREN-1411 $63.33 TCC Plus vs $135.30 standard). Tuition exemptions/waivers don't cover TCC Plus. Confidence: HIGH on program name, IA structure, per-course model; MEDIUM on precise pricing.",
        "notes": "TCC Plus branded locally but explicitly \"Powered by First Day\" (Barnes & Noble College backend). Charge appears automatically when registering for TCC Plus section, billed with tuition as course materials line item. Prices course-specific with sample table rather than rate card."
    },
    {
        "name": "Houston Community College",
        "ia_program_name": "First Day – Inclusive Access Program",
        "cost_model": "per-course",
        "price": "Varies by course; no official unified dollar amount published",
        "source_url": "http://www.hccs.edu/resources-for/current-students/hcc-textbook-saving-program/first-day---inclusive-access-program/",
        "ai_results": "Searched: \"Houston Community College First Day inclusive access program\", \"HCC First Day textbook saving program fee\". HCC's page describes First Day as BNC/publisher partnership delivering digital course materials on/before first day of class at below-market rates. Participating courses include cost as course material fee on student account. Students auto-opted in, with opt-out option available. First Day fee appears on student bill, covered by financial aid. Percentage savings emphasized but no uniform per-course price published. Confidence: HIGH on program identity and IA billing model; LOW-MEDIUM on exact pricing.",
        "notes": "HCC runs classic Barnes & Noble First Day IA program, branded as part of \"Textbook Saving Program.\" Charges attached to specific First Day sections as dedicated line item. Financial aid applies but students must manage opt-out by deadline."
    },
    {
        "name": "Dallas College",
        "ia_program_name": "IncludED",
        "cost_model": "included-tuition",
        "price": "$20/credit hour premium (tuition $59→$79 for Dallas County residents to include materials)",
        "source_url": "https://blog.dallascollege.edu/2020/04/better-when-bundled-say-hello-to-dcccds-tuition-learning-materials-combo/",
        "ai_results": "Searched: \"Dallas College IncludED tuition learning materials combo\", \"DCCCD IncludED $79 per credit hour\". Dallas College blog explains under IncludED, learning materials included in cost of tuition. For Dallas County residents, tuition increased from $59 to $79/credit hour, additional $20 covers textbooks and required course materials. Students can opt out and receive $20/hr reduction in tuition, reverting to $59/hr without materials. IncludED covers textbooks, access codes, and some supplies bundled into tuition premium. Confidence: HIGH on program name, cost model, and $20/hr pricing.",
        "notes": "Dallas College IncludED is a true equitable/inclusive access tuition-bundled model: IA cost embedded directly in per-credit tuition rate. Functionally $20/credit hour though presented as single $79/hr tuition for residents. Students can opt out and immediately see tuition decrease by $20/hr."
    },
    {
        "name": "Liberty University",
        "ia_program_name": "Inclusive Access (Liberty University)",
        "cost_model": "flat-rate-credit",
        "price": "$38/credit hour (Inclusive Access Fee) for eligible online graduate courses; waived for online undergrads",
        "source_url": "https://www.liberty.edu/information-services/inclusive-access/",
        "ai_results": "Searched: \"Liberty University Inclusive Access fee $38 per hour\", \"Liberty Inclusive Access course fees pdf\". Liberty's page describes IA delivering digital course materials within learning platforms. Online undergrad students don't pay (IA fees waived), graduate students in IA courses pay lower bundled costs. Fee schedules list explicit \"Inclusive Access Fee - $38 per hour\" for certain courses. Tuition & Fees page confirms online undergrads get electronic materials at no additional cost while grad students may see the fee. Confidence: HIGH on IA program and $38/credit hour fee for graduate-level courses.",
        "notes": "Liberty's implementation is unusual: online undergraduates have IA fees waived (materials effectively tuition-included), while graduate online students pay stated $38/credit Inclusive Access fee. Program uses generic \"Inclusive Access\" label."
    },
    {
        "name": "Full Sail University",
        "ia_program_name": "None found (books and supplies included in program tuition)",
        "cost_model": "included-tuition",
        "price": "Not listed as separate fee; textbooks bundled into total program tuition",
        "source_url": "https://www.fullsail.edu/admissions/tuition",
        "ai_results": "Searched: \"Full Sail inclusive access textbooks included tuition\", \"Full Sail books and supplies cost\", \"Full Sail Follett Access First Day\". Full Sail's tuition page states tuition prices include all costs for the full degree program, including textbooks, manuals, media, and required materials. PDFs confirm material costs part of single package price, not billed per term/course. No opt-out or per-course materials fee found. No evidence of Follett ACCESS, First Day, or similar IA-branded program. Confidence: HIGH that Full Sail does not run a separate IA billing scheme.",
        "notes": "Full Sail is a \"materials-included\" tuition model — one packaged program cost covers all texts and media. No incremental billing or opt-out typical of IA programs. Record as \"None found\" for IA Program Name with \"included-tuition\" as Cost Model."
    },
    {
        "name": "NUC University",
        "ia_program_name": "None found",
        "cost_model": "unknown",
        "price": "Not listed",
        "source_url": "https://online.nuc.edu/wp-content/uploads/2024/03/15-NUC_University-Textbooks.pdf",
        "ai_results": "Searched: \"NUC University inclusive access textbooks\", \"NUC University Follett ACCESS\", \"NUC University course materials fee Puerto Rico\". NUC's textbook list PDF lists specific textbooks/ISBNs by course and campus, indicating traditional individual purchase model. General catalogs detail tuition/fees but don't mention IA, Follett ACCESS, First Day, or equitable access. No bookstore IA page found. Limited English documentation. Confidence: LOW-MEDIUM — best available data suggests no IA program, but documentation may be incomplete.",
        "notes": "Recorded as \"None found\" with unknown cost model. Lack of evidence is not strong proof of absence — may need to revisit if internal or student-facing bookstore portal for NUC becomes accessible."
    },
    {
        "name": "DeVry University-Illinois",
        "ia_program_name": "None found",
        "cost_model": "unknown",
        "price": "Not listed",
        "source_url": "https://www.devry.edu/tuition-and-financial-aid/tuition-and-fees.html",
        "ai_results": "Searched: \"DeVry University inclusive access textbooks\", \"DeVry Follett ACCESS\", \"DeVry First Day course materials\". DeVry's tuition/fees pages list tuition by credit hour and admin fees but no line item for inclusive access or course materials fee. Required texts/digital resources appear in online course shells via publisher platforms (Pearson, McGraw Hill) but seem to be standard adoptions not a named IA program. No branded IA program or systematic auto-billed materials fee with opt-out found. Confidence: LOW — public documentation thin.",
        "notes": "Given DeVry's largely online focus and reliance on proprietary courseware, some materials charges may be baked into tuition, but nothing in official pages resembles a transparent IA program. Explicitly reflects uncertainty."
    },
    {
        "name": "American River College",
        "ia_program_name": "None (Zero Textbook Cost / Low Cost emphasis instead)",
        "cost_model": "unknown",
        "price": "Not listed",
        "source_url": "https://arc.losrios.edu/admissions/enrollment-and-eservices/zero-textbook-costs",
        "ai_results": "Searched: \"American River College inclusive access\", \"ARC Los Rios Follett ACCESS First Day\". ARC's ZTC page explains ARC/Los Rios promote Zero Textbook Cost (ZTC) and Low Cost courses ($0 or max $30 for materials). Emphasizes OER, library-licensed content, and free/low-cost materials. No IA billing program referenced, no IA fee in district fee schedules, no Follett/BNC branding found. Confidence: HIGH that ARC pursues cost-reduction via OER/ZTC rather than IA-style auto-billing.",
        "notes": "ARC represents the opposite strategy of IA schools: labels and promotes ZTC/low-cost sections, encourages OER adoption. No mandatory book fee or IA program found."
    },
    {
        "name": "Valencia College",
        "ia_program_name": "None found",
        "cost_model": "unknown",
        "price": "Not listed",
        "source_url": "https://valenciacollege.edu/admissions/dual-enrollment/documents/ucf-valencia-college-dual-enrollment-instructions-for-students.pdf",
        "ai_results": "Searched: \"Valencia College inclusive access textbooks\", \"Valencia Follett ACCESS\", \"Valencia College First Day program\". Main Valencia tuition/bookstore pages don't mention IA. Only IA reference found in UCF-Valencia dual enrollment PDF, which warns dual-enrollment students about UCF's First Day fees and instructs them NOT to opt into UCF's First Day for dual-enrollment courses — implying Valencia itself doesn't operate IA. No Valencia-branded IA, automatic textbook billing, or opt-out instructions found. Confidence: MEDIUM-LOW.",
        "notes": "Important: do NOT attribute UCF's First Day IA program to Valencia College. The only IA mention is in context of UCF's program. No Valencia-run IA program found."
    },
    {
        "name": "Purdue University-Main Campus",
        "ia_program_name": "None found",
        "cost_model": "unknown",
        "price": "Not listed",
        "source_url": "https://lib.purdue.edu/help/course-material-affordability/",
        "ai_results": "Searched: \"Purdue University West Lafayette inclusive access bookstore\", \"Purdue main campus Follett ACCESS\". Purdue Libraries promotes \"Affordable Course Materials\" via OER/low-cost options but no IA billing program found at main campus. Purdue Northwest (PNW) has $304/semester IA, Purdue Fort Wayne has per-course IA — these are separate campuses. No evidence of mandatory textbook fees at West Lafayette. Confidence: HIGH that main campus does not have IA.",
        "notes": "Do NOT confuse with PNW ($304/semester flat-rate) or Fort Wayne. Main Purdue emphasizes OER over IA billing."
    },
    {
        "name": "Grand Canyon University",
        "ia_program_name": "Canyon Connect",
        "cost_model": "per-course",
        "price": "$130/course undergrad (2026-27); $140 grad; $150 doctoral",
        "source_url": "https://www.gcu.edu/tuition/other-fees",
        "ai_results": "Searched: \"GCU Canyon Connect BibliU fee\". Official fees page lists Canyon Connect fees by program ($130-$500/course). BibliU delivery in LMS. No opt-out found. Tiered pricing by program level. Confidence: HIGH.",
        "notes": "Proprietary IA (BibliU-powered). No opt-out found. Tiered pricing: $130 undergrad, $140 grad, $150 doctoral per course."
    },
]


def curl_api(method, url, data=None):
    """Make an API call via curl subprocess (avoids Python SSL hangs)."""
    cmd = ["curl", "-s", "--max-time", "15", "-w", "\n%{http_code}", url,
           "-X", method,
           "-H", f"Authorization: Bearer {TOKEN}",
           "-H", "Content-Type: application/json",
           "-H", "Notion-Version: 2022-06-28"]
    if data:
        cmd.extend(["-d", json.dumps(data)])
    result = subprocess.run(cmd, capture_output=True, text=True)
    lines = result.stdout.strip().rsplit("\n", 1)
    body = lines[0] if len(lines) > 1 else ""
    code = lines[-1] if lines else "0"
    return code, body


def main():
    # Step 1: Fetch all pages to map school name → page ID
    print("Fetching board pages...")
    code, body = curl_api("POST", f"https://api.notion.com/v1/databases/{DB_ID}/query", {"page_size": 100})
    data = json.loads(body)
    name_to_id = {}
    for p in data.get("results", []):
        title = p.get("properties", {}).get("School Name", {}).get("title", [])
        if title:
            name_to_id[title[0]["plain_text"].strip()] = p["id"]
    print(f"  Found {len(name_to_id)} pages.\n")

    # Step 2: Update each school
    ok = 0
    fail = 0
    for school in SCHOOLS:
        name = school["name"]
        page_id = name_to_id.get(name)
        if not page_id:
            print(f"  ❌ NOT FOUND: {name}")
            fail += 1
            continue

        payload = {
            "properties": {
                "IA Program Name": {"rich_text": [{"text": {"content": school["ia_program_name"][:2000]}}]},
                "Cost Model": {"select": {"name": school["cost_model"]}},
                "Price": {"rich_text": [{"text": {"content": school["price"][:2000]}}]},
                "Source URL": {"url": school["source_url"]},
                "AI Research Results": {"rich_text": [{"text": {"content": school["ai_results"][:2000]}}]},
                "Agent Notes": {"rich_text": [{"text": {"content": school["notes"][:2000]}}]},
                "Status": {"select": {"name": "Review"}}
            }
        }

        code, _ = curl_api("PATCH", f"https://api.notion.com/v1/pages/{page_id}", payload)
        if code == "200":
            print(f"  ✅ {name}")
            ok += 1
        else:
            print(f"  ❌ {name} (HTTP {code})")
            fail += 1
        time.sleep(0.4)

    print(f"\n{'='*40}")
    print(f"  SYNC COMPLETE: {ok} updated, {fail} failed")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()
