# IA Research Log — 2026-03-10

## Notion MCP status
- Query and patch calls to the Notion MCP server fail with `missing_version` because the server sends Notion-Version `2025-02-18`. The Notion API now requires one of: 2021-05-11, 2021-05-13, 2021-08-16, 2022-02-22, 2022-06-28, 2025-09-03, or 2026-03-11. GET requests work; POST/PATCH do not.
- Used local `.board_snapshot.json` to identify the first five `Not Started` schools.
- No Notion updates were applied (blocked by MCP version error).

## Schools researched (intended updates)

### 1) California State University–Sacramento
- Notion page ID: 31fb11a2-332a-8108-a8e2-f42f00df07b0
- IA Program Name: Course-by-Course Affordable Access Program (Hornet Bookstore)
- Cost Model: per-course
- Price: Not listed
- Source URL: https://www.bkstr.com/csusacramentostore/help-faq
- AI Research Results: Searched for “Sacramento State inclusive access,” “Hornet Bookstore access program,” and “Follett Access.” The Hornet Bookstore Help/FAQ page lists a “Course-by-Course Affordable Access Program” with a “Learn more” link, indicating a course-by-course IA program operated by the bookstore. The detail page was not accessible, and no pricing or billing specifics were visible on the FAQ page. Confidence: MEDIUM.
- Agent Notes: Program appears to exist but details (opt-out, billing timing, pricing) are not visible; follow the Access Program detail page or contact the bookstore for specifics.

### 2) Virginia Polytechnic Institute and State University (Virginia Tech)
- Notion page ID: 31fb11a2-332a-810f-8f0e-d420771fad40
- IA Program Name: None found
- Cost Model: unknown
- Price: Not listed
- Source URL: https://www.bkstr.com/virginiatechstore/help-faq
- AI Research Results: Searched for “Virginia Tech inclusive access,” “First Day,” and bookstore access programs. Reviewed the Virginia Tech Bookstore Help/FAQ and sitemap; neither lists an Access Program or Inclusive/First Day page. No official VT or bookstore page describing automatic textbook billing was found in the reviewed sources. Confidence: LOW.
- Agent Notes: Absence of evidence on the bookstore site doesn’t prove no IA program; may be handled elsewhere (departmental or LMS-based). Follow up with Student Accounts or bookstore staff.

### 3) Mt. San Antonio College
- Notion page ID: 31fb11a2-332a-8111-9f5c-c1a2dc43cfc6
- IA Program Name: None found (IA mentioned in committee notes only)
- Cost Model: unknown
- Price: Not listed
- Source URL: https://www.mtsac.edu/governance/committees/tide/2023_3_16_timc_meeting_notes.pdf
- AI Research Results: Searched for “Mt. SAC inclusive access,” “First Day,” and bookstore access programs. A Textbook & Instructional Materials Committee meeting notes PDF mentions “Questions: Inclusive access” and a bookstore RFP but provides no program details or pricing. No official IA program page was located. Confidence: LOW.
- Agent Notes: The committee note suggests IA may be under consideration; check SacBookRac/Bookstore and Student Accounts pages for any implemented program.

### 4) University of Georgia
- Notion page ID: 31fb11a2-332a-8117-9827-c7252e9ebdb3
- IA Program Name: None found
- Cost Model: unknown
- Price: Not listed
- Source URL: https://resources.coe.uga.edu/employees/faculty-resources/academic-programs/faculty-toolkit/
- AI Research Results: Searched for “UGA inclusive access,” “First Day,” and bookstore IA programs. Reviewed UGA course-materials resources (course reserves/OER) but did not find an IA billing program page in the sources reviewed. Confidence: LOW.
- Agent Notes: UGA may have an IA program via the bookstore or specific colleges; additional targeted search of UGA Bookstore/Student Accounts is recommended.

### 5) Colorado Technical University–Colorado Springs
- Notion page ID: 31fb11a2-332a-811a-8212-d6755de5d7d6
- IA Program Name: Course materials included in Total Program Cost (Virtual Campus) / Book Supplies & Course Materials Charge
- Cost Model: per-course (billed once per term)
- Price: $40 per course (undergrad) / $42 per course (grad); waived for eligible military tuition rate
- Source URL: https://www.coloradotech.edu/Media/Default/CTU/documents/tuition-and-financial-aid/Tuition-and-Fees-VIRTUAL-MIL.pdf
- AI Research Results: Searched for “CTU course materials fee” and “inclusive access.” CTU’s public pages state that the Virtual Campus Total Program Cost includes a custom suite of course materials and that the course materials charge is waived for eligible military tuition rates. A CTU Virtual Campus tuition & fees schedule lists a Book Supplies & Course Materials charge ($40 undergrad / $42 grad) with notes indicating the charge is derived per course and posted once each term after add/drop. This indicates automatic billing for course materials in online programs. Confidence: MEDIUM (Virtual Campus info; confirm Colorado Springs campus specifics).
- Agent Notes: Sources are for CTU Virtual Campus; on-ground Colorado Springs programs may differ. Verify campus-specific billing and opt-out policy (if any).
