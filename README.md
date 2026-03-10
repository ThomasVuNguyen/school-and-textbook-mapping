# School & Textbook Mapping — IA Research Pipeline

Automated research pipeline to discover Inclusive Access (IA) textbook programs across US colleges.

## Project Structure

```
├── scripts/
│   ├── pipeline/          # Core pipeline (actively used)
│   │   ├── research_pipeline.py   # Gemini CLI → IA research per school
│   │   ├── validate_results.py    # Cloudrift API → validate results
│   │   └── build_roster.py        # Build master college roster from IPEDS
│   ├── notion/            # Notion database sync scripts
│   ├── dashboard/         # Dashboard HTML + data generators
│   └── archive/           # One-off/obsolete scripts
├── data/
│   ├── raw/               # Unprocessed research output
│   ├── validated/         # Research results after validation
│   └── reference/         # Master lists (college roster, state counts)
├── docs/                  # Research notes, prompt templates
├── .env                   # API keys (gitignored)
└── .venv/                 # Python virtual environment
```

## Quick Start

```bash
# Activate venv
source .venv/bin/activate

# 1. Research: run Gemini CLI on a batch of schools
python scripts/pipeline/research_pipeline.py --batch-size 100

# 2. Validate: check results against source URLs
python scripts/pipeline/validate_results.py --input data/raw/research_results.csv \
                                            --output data/validated/research_results_validated.csv

# 3. Build roster (if needed)
python scripts/pipeline/build_roster.py
```

## Dependencies

```bash
pip install openai requests python-dotenv
```

## Environment Variables (`.env`)

```
CLOUDRIFT_API_KEY=your_key_here
CLOUDRIFT_BASE_URL=https://llm-gateway.cloudrift.ai/v1
CLOUDRIFT_MODEL=google/gemma-3-12b-it
```
