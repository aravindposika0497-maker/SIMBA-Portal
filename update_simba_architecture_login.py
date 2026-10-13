from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).resolve().parent
HTML = ROOT / 'templates' / 'login.html'
LOGIN_CSS = ROOT / 'static' / 'css' / 'login.css'
PORTAL_CSS = ROOT / 'static' / 'css' / 'portal.css'

for p in (HTML, LOGIN_CSS, PORTAL_CSS):
    if not p.exists():
        raise SystemExit(f"Could not find {p.relative_to(ROOT)}. Put this script in the project folder next to wsgi.py.")
    backup = p.with_name(p.name + '.bak-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(p, backup)
    print(f'Backup: {backup.name}')

html = HTML.read_text(encoding='utf-8')
# Keep the existing login form/authentication, but simplify the left branding panel.
start = html.find('      <div class="brand-copy">')
end = html.find('      <div class="brand-footer">', start)
if start >= 0 and end >= 0:
    end2 = html.find('</div>', end) + len('</div>')
    html = html[:start] + html[end2:]
# Normalize the brand label without changing form actions or authentication.
html = html.replace('SIMBA<span class="brand-slash"> / </span>DATA', 'SIMBA')
HTML.write_text(html, encoding='utf-8')

login_rules = r'''
/* SIMBA refined login branding: compact, calm, and responsive */
.login-brand-panel{min-height:100vh;justify-content:center;align-items:flex-start;padding:clamp(28px,5vw,64px);}
.login-brand{font-size:clamp(22px,2.4vw,30px);letter-spacing:.12em;animation:simbaBrandIn .75s ease-out both;}
.login-mark{width:42px;height:42px;border-radius:13px;font-size:20px;}
.login-brand-panel:before{opacity:.14;background-size:56px 56px;}
.login-brand-panel:after{opacity:.32;}
.login-brand-panel:has(.login-brand)::before{animation:simbaGridDrift 30s linear infinite;}
.login-brand-panel .brand-orbit{opacity:.45;}
.login-brand-panel::marker{content:none;}
@keyframes simbaBrandIn{from{opacity:0;transform:translateY(12px);letter-spacing:.2em}to{opacity:1;transform:translateY(0);letter-spacing:.12em}}
@keyframes simbaGridDrift{from{background-position:0 0,0 0}to{background-position:56px 56px,-56px 56px}}
@media(max-width:900px){.login-brand-panel{min-height:180px;padding:28px;justify-content:center}.login-brand{font-size:24px}.login-mark{width:38px;height:38px}}
@media(prefers-reduced-motion:reduce){.login-brand,.login-brand-panel:before{animation:none!important}}
'''
css = LOGIN_CSS.read_text(encoding='utf-8')
if 'SIMBA refined login branding' not in css:
    LOGIN_CSS.write_text(css + '\n' + login_rules, encoding='utf-8')

portal_rules = r'''
/* Equal-sized medallion cards in the Databricks Lakehouse architecture stage */
.architecture-step.lake{display:flex;flex-direction:column;min-height:230px;}
.architecture-step.lake .medallion{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));align-items:stretch;gap:10px;width:100%;}
.architecture-step.lake .medallion span:nth-child(odd){box-sizing:border-box;min-width:0;min-height:112px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:14px 8px;border:1px solid var(--line);border-radius:12px;background:#fff;color:var(--ink);font-size:14px;font-weight:750;}
.architecture-step.lake .medallion span:nth-child(even){display:none;}
.architecture-step.lake .medallion span:nth-child(odd)::after{display:block;margin-top:8px;color:var(--muted);font-size:12px;font-weight:500;}
.architecture-step.lake .medallion span:nth-child(1)::after{content:'Raw';}
.architecture-step.lake .medallion span:nth-child(3)::after{content:'Cleaned';}
.architecture-step.lake .medallion span:nth-child(5)::after{content:'Business-ready';}
@media(max-width:760px){.architecture-step.lake{min-height:0}.architecture-step.lake .medallion{gap:6px}.architecture-step.lake .medallion span:nth-child(odd){min-height:92px;padding:10px 4px;font-size:12px}}
'''
css = PORTAL_CSS.read_text(encoding='utf-8')
if 'Equal-sized medallion cards' not in css:
    PORTAL_CSS.write_text(css + '\n' + portal_rules, encoding='utf-8')

print('\nUpdated SIMBA login branding and equal-sized Bronze/Silver/Gold architecture cards.')
print('Authentication routes and backend/data code were not changed.')
print('Restart Flask and hard-refresh the browser (Ctrl+F5) to see the changes.')
