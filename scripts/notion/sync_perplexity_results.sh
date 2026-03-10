#!/bin/bash
# Sync Perplexity research results into the Notion Kanban board
# Each school gets: IA Program Name, Cost Model, Price, Source URL, AI Research Results, Agent Notes, Status → Review

DB_ID="31fb11a2-332a-81a8-afcf-e21dbe68e8a3"
TOKEN="${NOTION_TOKEN}"

# First, get all page IDs mapped to school names
echo "Fetching board pages..."
curl -s --max-time 15 "https://api.notion.com/v1/databases/${DB_ID}/query" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Notion-Version: 2022-06-28" \
  -d '{"page_size":100}' -o /tmp/board_for_sync.json

echo "Mapping school names to page IDs..."

find_page_id() {
  local school="$1"
  python3 -c "
import json
with open('/tmp/board_for_sync.json') as f:
    d=json.load(f)
for p in d.get('results',[]):
    t=p.get('properties',{}).get('School Name',{}).get('title',[])
    if t and t[0]['plain_text'].strip().lower()=='${school}'.lower():
        print(p['id'])
        break
"
}

update_school() {
  local PAGE_ID="$1"
  local SCHOOL="$2"
  local IA_NAME="$3"
  local COST_MODEL="$4"
  local PRICE="$5"
  local SOURCE_URL="$6"
  local AI_RESULTS="$7"
  local NOTES="$8"

  if [ -z "$PAGE_ID" ]; then
    echo "  ❌ SKIP: Could not find page ID for: $SCHOOL"
    return 1
  fi

  # Build the JSON payload
  local PAYLOAD=$(python3 -c "
import json
data = {
  'properties': {
    'IA Program Name': {'rich_text': [{'text': {'content': '''${IA_NAME}'''}}]},
    'Cost Model': {'select': {'name': '''${COST_MODEL}'''}},
    'Price': {'rich_text': [{'text': {'content': '''${PRICE}'''}}]},
    'Source URL': {'url': '''${SOURCE_URL}'''},
    'AI Research Results': {'rich_text': [{'text': {'content': '''${AI_RESULTS}'''[:2000]}}]},
    'Agent Notes': {'rich_text': [{'text': {'content': '''${NOTES}'''[:2000]}}]},
    'Status': {'select': {'name': 'Review'}}
  }
}
print(json.dumps(data))
")

  local HTTP_CODE=$(curl -s --max-time 15 -o /dev/null -w "%{http_code}" \
    "https://api.notion.com/v1/pages/${PAGE_ID}" \
    -X PATCH \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -H "Notion-Version: 2022-06-28" \
    -d "$PAYLOAD")

  if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ $SCHOOL"
  else
    echo "  ❌ $SCHOOL (HTTP $HTTP_CODE)"
  fi
  sleep 0.4
}

echo ""
echo "=== Syncing 12 schools ==="
echo ""
