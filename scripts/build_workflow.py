"""Generates workflows/ai-lead-triage.json so the Code node always matches scripts/triage_logic.js."""
import json, pathlib
root = pathlib.Path(__file__).resolve().parents[1]
code = (root / "scripts" / "triage_logic.js").read_text()

def node(id_, name, type_, ver, pos, params, creds=None):
    n = {"id": id_, "name": name, "type": type_, "typeVersion": ver, "position": pos, "parameters": params}
    if creds: n["credentials"] = creds
    return n

nodes = [
    node("1", "Lead Webhook", "n8n-nodes-base.webhook", 2, [0, 200],
         {"httpMethod": "POST", "path": "lead-intake", "responseMode": "responseNode"}),
    node("2", "Normalize & Score", "n8n-nodes-base.code", 2, [220, 200], {"jsCode": code}),
    node("3", "Is Spam?", "n8n-nodes-base.if", 2, [440, 200], {"conditions": {
        "options": {"caseSensitive": True, "typeValidation": "strict"}, "combinator": "and",
        "conditions": [{"id": "c1", "leftValue": "={{ $json.spam }}", "rightValue": True,
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True}}]}}),
    node("4", "AI Draft Reply", "n8n-nodes-base.httpRequest", 4.2, [680, 300], {
        "method": "POST", "url": "={{ ($env.OPENAI_BASE_URL || 'https://api.openai.com/v1') + '/chat/completions' }}",
        "sendHeaders": True, "headerParameters": {"parameters": [{"name": "Authorization", "value": "=Bearer {{ $env.OPENAI_API_KEY }}"}]},
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({model: $env.OPENAI_MODEL || 'gpt-4o-mini', max_tokens: 200, messages: [{role: 'system', content: 'You write short, warm, professional replies for a local service business. Never promise prices or exact times. Max 80 words.'}, {role: 'user', content: 'Customer: ' + $json.name + '\\nService: ' + $json.service + '\\nMessage: ' + $json.message + '\\nUrgent: ' + $json.urgent}]}) }}",
        "options": {"timeout": 30000}}),
    node("5", "Build Email", "n8n-nodes-base.code", 2, [900, 300], {"jsCode":
        "const lead = $('Normalize & Score').first().json;\n"
        "let reply;\ntry { reply = $json.choices[0].message.content.trim(); } catch (e) { reply = null; }\n"
        "if (!reply) reply = `Hi ${lead.name}, thanks for contacting ${$env.BUSINESS_NAME || 'us'}. We received your request and will get back to you shortly.`;\n"
        "return [{ json: { ...lead, reply } }];"}),
    node("6", "Send Reply to Lead", "n8n-nodes-base.gmail", 2.1, [1120, 300], {
        "resource": "message", "operation": "send", "sendTo": "={{ $json.email }}",
        "subject": "={{ 'Re: your enquiry - ' + ($env.BUSINESS_NAME || 'We got your message') }}",
        "message": "={{ $json.reply }}", "options": {}}),
    node("7", "Is HOT?", "n8n-nodes-base.if", 2, [1340, 300], {"conditions": {
        "options": {"caseSensitive": True, "typeValidation": "strict"}, "combinator": "and",
        "conditions": [{"id": "c2", "leftValue": "={{ $('Build Email').item.json.tier }}", "rightValue": "HOT",
                        "operator": {"type": "string", "operation": "equals"}}]}}),
    node("8", "Alert Owner (HOT)", "n8n-nodes-base.gmail", 2.1, [1560, 200], {
        "resource": "message", "operation": "send", "sendTo": "={{ $env.OWNER_ALERT_EMAIL }}",
        "subject": "={{ 'HOT lead: ' + $('Build Email').item.json.name }}",
        "message": "={{ 'Score ' + $('Build Email').item.json.score + '\\nPhone: ' + $('Build Email').item.json.phone + '\\n\\n' + $('Build Email').item.json.message }}", "options": {}}),
    node("9", "Log to Google Sheet", "n8n-nodes-base.googleSheets", 4.5, [1780, 300], {
        "operation": "append", "documentId": {"__rl": True, "mode": "id", "value": "={{ $env.GOOGLE_SHEET_ID }}"},
        "sheetName": {"__rl": True, "mode": "name", "value": "Leads"},
        "columns": {"mappingMode": "defineBelow", "value": {
            "Received": "={{ $('Build Email').item.json.receivedAt }}", "Name": "={{ $('Build Email').item.json.name }}",
            "Email": "={{ $('Build Email').item.json.email }}", "Phone": "={{ $('Build Email').item.json.phone }}",
            "Tier": "={{ $('Build Email').item.json.tier }}", "Score": "={{ $('Build Email').item.json.score }}",
            "Message": "={{ $('Build Email').item.json.message }}"}}, "options": {}}),
    node("10", "Respond OK", "n8n-nodes-base.respondToWebhook", 1.1, [2000, 300],
         {"respondWith": "json", "responseBody": "={{ { ok: true, tier: $('Build Email').item.json.tier } }}"}),
    node("11", "Respond Spam", "n8n-nodes-base.respondToWebhook", 1.1, [680, 100],
         {"respondWith": "json", "responseBody": "={{ { ok: true } }}"}),
]
def c(a, b, i=0): return {"node": b, "type": "main", "index": i}
connections = {
    "Lead Webhook": {"main": [[c(0, "Normalize & Score")]]},
    "Normalize & Score": {"main": [[c(0, "Is Spam?")]]},
    "Is Spam?": {"main": [[c(0, "Respond Spam")], [c(0, "AI Draft Reply")]]},
    "AI Draft Reply": {"main": [[c(0, "Build Email")]]},
    "Build Email": {"main": [[c(0, "Send Reply to Lead")]]},
    "Send Reply to Lead": {"main": [[c(0, "Is HOT?")]]},
    "Is HOT?": {"main": [[c(0, "Alert Owner (HOT)")], [c(0, "Log to Google Sheet")]]},
    "Alert Owner (HOT)": {"main": [[c(0, "Log to Google Sheet")]]},
    "Log to Google Sheet": {"main": [[c(0, "Respond OK")]]},
}
# AI node must not kill the run if the LLM is down
for n in nodes:
    if n["name"] == "AI Draft Reply": n["onError"] = "continueRegularOutput"
wf = {"name": "AI Lead Triage & Auto-Reply", "nodes": nodes, "connections": connections,
      "settings": {"executionOrder": "v1"}, "pinData": {}, "meta": {"templateCredsSetupCompleted": False}}
(root / "workflows" / "ai-lead-triage.json").write_text(json.dumps(wf, indent=2))
print("wrote workflow with", len(nodes), "nodes")
