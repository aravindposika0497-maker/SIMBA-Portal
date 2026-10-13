from pathlib import Path
import re, sys

# Run this script from the existing SIMBAPORTAL project root (the folder containing wsgi.py).
root = Path.cwd()
js = root / 'static' / 'js' / 'portal.js'
if not js.exists():
    print('ERROR: static/js/portal.js not found. Open PowerShell in your existing SIMBAPORTAL folder and run this script there.')
    sys.exit(1)
s = js.read_text(encoding='utf-8')
if 'SIMBA_INPLACE_TALK_TO_DATA_PATCH' in s:
    print('Talk to Data and Governance sample data patch is already present. No changes made.')
    sys.exit(0)

# Add Talk to Data to the existing navigation.
old = "{ id: 'governance', label: 'Security & Governance', icon: 'shield', group: 'Governance' },"
new = old + "\n    { id: 'talk-data', label: 'Talk to Data', icon: 'chart', group: 'Workspace' },"
if old not in s:
    print('ERROR: Could not locate the existing navigation entry. No changes made.')
    sys.exit(1)
s = s.replace(old, new, 1)

# Supply clearly labelled illustrative records only when the live grants query is empty.
old = "const rows = grants().filter((x) => contains(`${x.grantee} ${x.securable} ${x.privilege}`, ui.grantSearch)"
new = "const sourceGrants = grants();\n      const illustrative = [\n        { grantee: 'demo-analytics-team', grantee_type: 'GROUP', securable: 'simba_catalog.gold.customer_360', securable_type: 'TABLE', privilege: 'SELECT', path: 'Direct grant', grantor: 'sample-admin' },\n        { grantee: 'demo-data-engineers', grantee_type: 'GROUP', securable: 'simba_catalog.bronze.kafka_events', securable_type: 'TABLE', privilege: 'SELECT', path: 'Direct grant', grantor: 'sample-admin' },\n        { grantee: 'demo-platform-admins', grantee_type: 'GROUP', securable: 'simba_catalog', securable_type: 'CATALOG', privilege: 'USE CATALOG', path: 'Direct grant', grantor: 'sample-admin' },\n        { grantee: 'demo-powerbi-service', grantee_type: 'SERVICE PRINCIPAL', securable: 'simba_catalog.gold.transaction_summary', securable_type: 'TABLE', privilege: 'SELECT', path: 'Inherited', grantor: 'sample-admin' },\n        { grantee: 'demo-risk-analysts', grantee_type: 'GROUP', securable: 'simba_catalog.silver.customer_profile', securable_type: 'TABLE', privilege: 'SELECT', path: 'Direct grant', grantor: 'sample-admin' },\n        { grantee: 'demo-data-quality', grantee_type: 'GROUP', securable: 'simba_catalog.silver.transaction', securable_type: 'TABLE', privilege: 'SELECT', path: 'Inherited', grantor: 'sample-admin' },\n        { grantee: 'demo-operations', grantee_type: 'GROUP', securable: 'simba_catalog.gold.daily_kpis', securable_type: 'VIEW', privilege: 'SELECT', path: 'Direct grant', grantor: 'sample-admin' },\n        { grantee: 'demo-ml-team', grantee_type: 'GROUP', securable: 'simba_catalog.gold.customer_features', securable_type: 'TABLE', privilege: 'SELECT', path: 'Inherited', grantor: 'sample-admin' },\n      ];\n      const displayGrants = sourceGrants.length ? sourceGrants : illustrative;\n      const rows = displayGrants.filter((x) => contains(`${x.grantee} ${x.securable} ${x.privilege}`, ui.grantSearch)"
if old not in s:
    print('ERROR: Could not locate governance rows code. No changes made.')
    sys.exit(1)
s = s.replace(old, new, 1)
s = s.replace("'No grants visible to the portal service principal') : 'Grants not loaded'),", "'No grants visible to the portal service principal') : 'Grants not loaded'),", 1) # keep existing empty copy
# Update governance panel to visibly disclose when examples are being shown.
old = "panel('Who can access what?', 'Read from Unity Catalog information_schema. One row per grant.', null, filters.el, list.el));"
new = "panel('Who can access what?', grants().length ? 'Read from Unity Catalog information_schema. One row per grant.' : 'ILLUSTRATIVE SAMPLE DATA — not live Unity Catalog permissions.', null, filters.el, list.el));"
if old in s: s = s.replace(old, new, 1)

# Insert a functional local demo chat page before governance page declaration.
marker = "  Pages.governance = () => {"
chat = r'''  // SIMBA_INPLACE_TALK_TO_DATA_PATCH: local demo chat; no live AI/backend integration claimed.
  Pages['talk-data'] = () => {
    const prompts = [
      'How does Plumery Kafka data reach Bronze?',
      'Explain the Bronze, Silver and Gold layers',
      'How is customer data governed?',
      'Which tables support transaction analytics?',
      'How does Power BI consume Gold data?'
    ];
    const answerFor = (q) => {
      const t = q.toLowerCase();
      if (t.includes('kafka') || t.includes('plumery') || t.includes('bronze')) return 'Plumery events are expected to be consumed from Amazon MSK/Kafka by a Databricks Structured Streaming job and written to a Bronze Delta table. Validate broker connectivity, topic permissions, schema and replay/retention before treating this flow as live.';
      if (t.includes('layer') || t.includes('silver') || t.includes('gold')) return 'Bronze stores raw source data, Silver applies validation, deduplication and standardisation, and Gold contains business-ready models for reporting and analytics. These are the intended SIMBA design layers; pipeline execution is not verified by this demo.';
      if (t.includes('govern') || t.includes('customer data') || t.includes('access')) return 'Unity Catalog is the intended governance layer for catalog/schema/table permissions, ownership, lineage and audit. Request access through the approved process; this demo cannot grant or verify permissions.';
      if (t.includes('power bi') || t.includes('report') || t.includes('transaction')) return 'The intended reporting path is Power BI → Databricks SQL → curated Gold tables/views. Candidate domains include customer, transaction, transfer, payment and beneficiary analytics. Confirm final columns and table availability with the data owner.';
      return 'This is a local SIMBA demo assistant, not connected to a live model or Databricks query endpoint. Try one of the suggested questions about Kafka ingestion, medallion layers, governance or Power BI.';
    };
    const transcript = h('div', { class: 'talk-transcript', 'aria-live': 'polite' },
      h('div', { class: 'talk-msg assistant' }, h('b', null, 'SIMBA Data Assistant'), h('p', null, 'Ask about the planned data platform. Responses are illustrative and do not query live systems.')));
    const input = h('input', { class: 'talk-input', type: 'text', placeholder: 'Ask about Kafka, data layers, governance…', 'aria-label': 'Ask SIMBA Data Assistant' });
    const send = (question) => {
      const q = String(question || input.value || '').trim(); if (!q) return;
      transcript.append(h('div', { class: 'talk-msg user' }, h('b', null, 'You'), h('p', null, q)));
      transcript.append(h('div', { class: 'talk-msg assistant' }, h('b', null, 'SIMBA Data Assistant · Demo'), h('p', null, answerFor(q))));
      input.value = ''; transcript.scrollTop = transcript.scrollHeight;
    };
    const form = h('form', { class: 'talk-form', onsubmit: (e) => { e.preventDefault(); send(); } }, input, h('button', { class: 'btn', type: 'submit' }, 'Send'));
    const suggestions = h('div', { class: 'talk-prompts' }, prompts.map((p) => h('button', { class: 'btn btn-small', type: 'button', onclick: () => send(p) }, p)));
    const el = h('div', null, head('Talk to Data', 'Ask questions about SIMBA architecture, ingestion, governance and analytics.'),
      h('div', { class: 'talk-demo-note' }, 'DEMO MODE · Responses are predefined examples. No live AI, database or Databricks query is connected.'),
      panel('SIMBA Data Assistant', 'Choose a prompt or enter your own question.', null, suggestions, transcript, form));
    return { el, update: () => {} };
  };

'''
if marker not in s:
    print('ERROR: Could not find the governance page insertion point. No changes made.')
    sys.exit(1)
s = s.replace(marker, chat + marker, 1)
# Add compact styling from JS so this works without changing any other project files.
style = r'''/* SIMBA_INPLACE_TALK_TO_DATA_PATCH styles */
(function(){
 if(document.getElementById('simba-talk-data-style')) return;
 const st=document.createElement('style'); st.id='simba-talk-data-style'; st.textContent=`
 .talk-demo-note{padding:12px 14px;margin:0 0 16px;border:1px solid #e7c989;background:#fff8e8;color:#77551a;border-radius:10px;font-size:13px;font-weight:650}
 .talk-prompts{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}.talk-prompts .btn{white-space:normal;text-align:left;max-width:100%}
 .talk-transcript{display:flex;flex-direction:column;gap:10px;max-height:390px;overflow:auto;padding:14px;background:var(--surface-2,#f7f8fa);border:1px solid var(--border,#e2e6eb);border-radius:12px;margin:10px 0}
 .talk-msg{max-width:90%;padding:10px 13px;border-radius:10px;background:white;border:1px solid #e2e6eb}.talk-msg p{margin:5px 0 0;line-height:1.5}.talk-msg.user{align-self:flex-end;background:#eaf2ff;border-color:#c9dcff}.talk-msg.assistant{align-self:flex-start}
 .talk-form{display:flex;gap:8px}.talk-input{flex:1;min-width:0;padding:11px 13px;border:1px solid #cfd6df;border-radius:9px;font:inherit}
 `; document.head.appendChild(st);
})();
'''
s += '\n' + style
js.write_text(s, encoding='utf-8')
print('SUCCESS: Updated the existing static/js/portal.js in place.')
print('Added: Talk to Data navigation/page with prompt buttons and demo answers.')
print('Added: 8 clearly labelled illustrative Governance records when live grants are empty.')
print('No new project folder created. Restart Flask and refresh the browser (Ctrl+F5).')
