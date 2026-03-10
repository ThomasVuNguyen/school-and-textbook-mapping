# School IA Research Task

You have access to a Notion MCP server. Your job is to research Inclusive Access (IA) textbook programs at universities and update a Notion Kanban board with your findings.

## Notion Database Info
- **Data Source ID** (use for querying): `31fb11a2-332a-8141-b685-000be13b3250`
- **Database ID** (use for other operations): `31fb11a2-332a-81a8-afcf-e21dbe68e8a3`

Use the **Data Source ID** when calling `API-query-data-source`. Use the **Database ID** for other operations if needed. When updating page properties, use the **page_id** from the query results.

## Step-by-Step Instructions

### 1. Query the Board
Use the Notion MCP to query the database above. Look for tickets where **Status = "Not Started"**. Pick the first 10 schools to research.

### 2. For EACH School

**a) Set Status → "In Progress"**
Update the ticket's Status property to "In Progress" using Notion MCP.

**b) Research the School's IA Program**
**IMPORTANT: Do NOT use curl — it is blocked in this environment. Use your built-in web search tool ONLY.**

Search for terms like:
- "{School Name} inclusive access"
- "{School Name} First Day textbook program"
- "{School Name} Follett Access bookstore"
- "{School Name} course materials fee bursar"
- "{School Name} textbook billing tuition bundled"

Be efficient — do 2-3 searches per school max, then move on. Don't spend more than 3 searches per school.

**c) Determine These Fields:**

| Field | Description |
|---|---|
| IA Program Name | e.g. "First Day™", "Follett Access", "IU eTexts", "None found" |
| Cost Model | One of: `per-course`, `flat-rate-term`, `flat-rate-credit`, `included-tuition`, `unknown` |
| Price | The actual dollar amount if found, otherwise "Not listed" |
| Source URL | The primary URL where you found the information |
| AI Research Results | Detailed paragraph: what you searched, what you found, confidence level (HIGH/MEDIUM/LOW) |
| Agent Notes | Key takeaways, warnings about data quality, things the reviewer should know |

**d) Update the Notion Ticket**
Using Notion MCP, update ALL the properties above on the ticket.

**e) Set Status → "Review"**
Change the Status to "Review".

### 3. What Counts as IA?
An Inclusive Access (IA) program is when a school **automatically charges students for digital textbooks** through their tuition/fees bill. Key indicators:
- Auto-opted-in, must opt-out
- Charged through bursar/student account (not bookstore checkout)
- Digital materials delivered through LMS (Canvas, Blackboard, etc.)
- Programs like "First Day", "Follett Access", "IncludED", "eTexts", "Day One Access"

**NOT IA:**
- Traditional bookstore purchases
- OER/Zero Textbook Cost programs
- Student chooses to buy online access codes themselves

### 4. Output Summary
After processing all schools, write a summary of what you updated to a file called `codex_research_log.md` in the current directory.

## Important Notes
- **Do NOT use curl** — it is blocked. Use web search tool only.
- Be efficient — 2-3 web searches per school max, then move on
- If you can't find IA info, mark as "None found" with confidence level
- Always include source URLs from your search results
- Do NOT make up information — if uncertain, say so
- Process up to 10 schools per run
- Append results to `codex_research_log.md` (don't overwrite previous runs)
