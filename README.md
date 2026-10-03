# n8n AI Lead Triage & Auto-Reply

An importable n8n workflow that catches website enquiries, filters spam, scores urgency, drafts a personalised AI reply, alerts the owner on HOT leads, and logs everything to Google Sheets.

## Problem
Home-service businesses (roofing, HVAC, plumbing, clinics, salons) lose jobs because enquiries sit unanswered for hours, and urgent ones look the same as junk in an inbox.

## Solution
A single webhook endpoint that responds to every real lead immediately, flags urgent/high-intent ones to the owner, and keeps a clean log — no custom server required.

## Features
- Webhook intake (`POST /webhook/lead-intake`) from any form, Facebook/Google lead ads, or Zapier-style tools
- Rule-based spam filter and transparent urgency/intent scoring (HOT / WARM / COLD / SPAM)
- LLM-drafted reply (any OpenAI-compatible API) with a safe fallback template if the AI call fails (`onError: continueRegularOutput`)
- Gmail reply to the lead; separate Gmail alert to the owner for HOT leads
- Google Sheets logging; JSON response to the caller
- No hardcoded secrets: everything via `$env` variables
- Tests validate workflow structure, secret hygiene, and run the scoring code in Node

## Architecture
```
Webhook -> Normalize & Score -> Spam? --yes--> Respond
                                  | no
                         AI Draft Reply (HTTP) -> Build Email -> Gmail reply
                                  -> HOT? --yes--> Alert Owner --> Google Sheets -> Respond OK
                                           --no-----------------> Google Sheets -> Respond OK
```

## Tech Stack
n8n (Webhook, Code, IF, HTTP Request, Gmail, Google Sheets, Respond to Webhook), OpenAI-compatible LLM API, Python + pytest + Node for tests.

## How It Works
Scoring (in `scripts/triage_logic.js`): urgent keywords +40, quote/price intent +20, phone provided +15, message > 60 chars +15, service selected +10. 60+ = HOT, 30+ = WARM. Spam keywords or invalid email = SPAM (no AI call, no email sent).
`scripts/build_workflow.py` generates `workflows/ai-lead-triage.json` from that file so the workflow and the tested logic never drift.

## Installation
1. In n8n: **Workflows -> Import from file** -> `workflows/ai-lead-triage.json`.
2. Attach your own Gmail and Google Sheets credentials to those nodes.
3. Create a Google Sheet with a `Leads` tab and headers: `Received, Name, Email, Phone, Tier, Score, Message`.
4. Set the environment variables below in your n8n instance (accessing `$env` must be allowed in your n8n settings).
5. Activate the workflow.

## Configuration
See `.env.example`: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `GOOGLE_SHEET_ID`, `OWNER_ALERT_EMAIL`, `BUSINESS_NAME`. Never commit real values.

## Usage
```bash
curl -X POST https://YOUR-N8N/webhook/lead-intake -H "Content-Type: application/json" -d @examples/sample_lead.json
pip install -r requirements.txt && pytest -q
python scripts/build_workflow.py   # regenerate the workflow JSON after editing the JS
```

## Example
`examples/sample_lead.json` (urgent AC failure + quote request + phone) scores as HOT in the test suite; `examples/sample_spam.json` is classified SPAM. The workflow has not been claimed to run in any production environment; import it and test with your own credentials.

## Project Structure
```
workflows/ai-lead-triage.json   importable n8n workflow
scripts/triage_logic.js         scoring logic (source of truth)
scripts/build_workflow.py       workflow generator
tests/test_workflow.py          structure, secrets, scoring tests
examples/                       sample payloads
```

## Future Improvements
WhatsApp/SMS reply branch, CRM (HubSpot/GoHighLevel) upsert, calendar booking link for HOT leads, duplicate detection, per-niche scoring profiles, LLM-based spam classification.

## Open-Source Foundation / Attribution
100% original workflow and code; no third-party repositories copied or adapted. Comply with anti-spam and privacy laws (CAN-SPAM, GDPR/PECR, Spam Act) when auto-replying.

## Author
Muhammad Waqas — AI Agents & Business Automation
