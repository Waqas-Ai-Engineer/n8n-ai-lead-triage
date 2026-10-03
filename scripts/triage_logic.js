// Source of truth for the "Normalize & Score" Code node. Copied into the workflow JSON by build_workflow.py.
const b = $input.first().json.body || $input.first().json;
const msg = String(b.message || '').trim();
const email = String(b.email || '').trim().toLowerCase();
const phone = String(b.phone || '').trim();
const urgent = /\b(asap|urgent|emergency|today|leak|burst|no heat|no ac|storm|flood)\b/i.test(msg);
const budget = /\b(quote|estimate|price|cost|budget|replace|install)\b/i.test(msg);
const spam = /\b(seo services|backlinks|crypto|casino|viagra|loan offer)\b/i.test(msg) || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);
let score = 0;
if (urgent) score += 40;
if (budget) score += 20;
if (phone) score += 15;
if (msg.length > 60) score += 15;
if (b.service) score += 10;
if (spam) score = 0;
const tier = spam ? 'SPAM' : score >= 60 ? 'HOT' : score >= 30 ? 'WARM' : 'COLD';
return [{ json: { name: b.name || 'there', email, phone, service: b.service || '', message: msg, score, tier, urgent, spam, receivedAt: new Date().toISOString() } }];
