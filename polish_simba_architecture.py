from pathlib import Path
import re, shutil, sys

ROOT = Path(__file__).resolve().parent
if not (ROOT / 'wsgi.py').exists() or not (ROOT / 'static').exists():
    print('ERROR: Put this script in the SIMBA project root (the folder containing wsgi.py, static, and templates).')
    sys.exit(1)

def backup(path):
    bak = path.with_suffix(path.suffix + '.bak')
    if not bak.exists():
        shutil.copy2(path, bak)

def append_once(path, marker, content):
    text = path.read_text(encoding='utf-8')
    if marker in text:
        print(f'Skipped existing update in {path.relative_to(ROOT)}')
        return
    backup(path)
    path.write_text(text.rstrip() + '\n\n' + content.strip() + '\n', encoding='utf-8')
    print(f'Updated {path.relative_to(ROOT)}')

# 1) Architecture: clearer equal-height cards, consistent spacing, responsive flow, animated stages.
portal_css = ROOT / 'static/css/portal.css'
append_once(portal_css, '/* SIMBA architecture polish v1 */', r'''/* SIMBA architecture polish v1 */
.architecture-page { animation: simbaPageIn .48s cubic-bezier(.2,.7,.2,1) both; }
.architecture-page > .head { margin-bottom: 22px; }
.architecture-callout { border: 1px solid rgba(225,29,72,.16); background: linear-gradient(110deg, #fff 0%, #fff5f6 100%); border-radius: 16px; padding: 16px 20px; margin: 0 0 22px; box-shadow: 0 8px 24px rgba(25,35,55,.035); }
.architecture-flow { display: grid; grid-template-columns: minmax(0,1fr) 28px minmax(0,1fr) 28px minmax(0,1.12fr) 28px minmax(0,1fr); gap: 12px; align-items: stretch; }
.architecture-step { display:flex; flex-direction:column; min-height:220px; height:100%; box-sizing:border-box; padding:20px 18px; border:1px solid #e0e7f0; border-radius:16px; background:linear-gradient(180deg,#fff 0%,#fbfcfe 100%); box-shadow:0 5px 16px rgba(20,32,55,.035); transition:transform .28s ease,box-shadow .28s ease,border-color .28s ease; }
.architecture-step::after { content:''; width:42px; height:3px; border-radius:3px; margin-top:auto; padding-top:16px; background:linear-gradient(90deg,#e11d48,#ff8061); background-clip:content-box; opacity:.9; }
.architecture-step:hover { transform:translateY(-5px); border-color:rgba(225,29,72,.4); box-shadow:0 16px 32px rgba(20,32,55,.1); }
.architecture-step b { font-size:15px; line-height:1.45; margin:10px 0 2px; color:#172033; }
.architecture-step p { color:#687995; font-size:13px; line-height:1.7; margin:8px 0 12px; }
.architecture-step .step-num { display:inline-flex; width:34px; height:34px; align-items:center; justify-content:center; border-radius:10px; background:#fff0f2; color:#d71936; font-weight:800; font-size:12px; box-shadow:inset 0 0 0 1px rgba(225,29,72,.09); }
.architecture-step.source { border-top:3px solid #369b66; }
.architecture-step.ingest { border-top:3px solid #cf4b8c; }
.architecture-step.lake { border-top:3px solid #1684b7; background:linear-gradient(160deg,#f0faff,#fff 75%); }
.architecture-step.consume { border-top:3px solid #27a99a; }
.architecture-arrow { align-self:center; display:flex; align-items:center; justify-content:center; color:#e11d48; font-size:25px; font-weight:700; animation:simbaArrowPulse 1.8s ease-in-out infinite; }
.medallion { display:grid; grid-template-columns:1fr auto 1fr auto 1fr; align-items:center; gap:5px; margin:14px 0 8px; }
.medallion span:nth-child(odd) { display:flex; align-items:center; justify-content:center; min-height:52px; padding:7px 5px; border:1px solid #dce5ef; border-radius:11px; background:#fff; font-weight:750; font-size:12px; box-shadow:0 3px 8px rgba(20,32,55,.035); }
.medallion span:nth-child(3) { background:#f4f7fb; }
.medallion span:nth-child(5) { background:#fff8e8; border-color:#f3dfae; }
.medallion span:nth-child(even) { color:#e11d48; font-size:14px; }
.architecture-figure { margin:0; overflow:hidden; border:1px solid #e1e8f0; border-radius:14px; background:#fff; }
.architecture-figure img { display:block; width:100%; height:auto; }
.architecture-figure figcaption { padding:12px 16px; color:#697995; font-size:12px; line-height:1.6; border-top:1px solid #edf1f6; }
@keyframes simbaPageIn { from {opacity:0; transform:translateY(9px)} to {opacity:1; transform:translateY(0)} }
@keyframes simbaArrowPulse { 0%,100% {transform:translateX(0);opacity:.65} 50% {transform:translateX(3px);opacity:1} }
/* Animate KPI values when a view renders; respects reduced-motion preferences. */
.metric .num { display:inline-block; transform-origin:left center; animation:simbaNumberIn .55s cubic-bezier(.2,.75,.25,1) both; }
.metric.flash .num { animation:simbaNumberPop .65s ease both; }
@keyframes simbaNumberIn { from {opacity:.15; transform:translateY(8px) scale(.96); filter:blur(2px)} to {opacity:1; transform:translateY(0) scale(1); filter:blur(0)} }
@keyframes simbaNumberPop { 0% {transform:scale(1);color:inherit} 35% {transform:scale(1.09);color:#e11d48} 100% {transform:scale(1);color:inherit} }
@media (max-width:1050px) { .architecture-flow { grid-template-columns:1fr; gap:10px; } .architecture-step { min-height:0; } .architecture-step::after { margin-top:12px; padding-top:0; } .architecture-arrow { transform:rotate(90deg); height:20px; animation:none; } }
@media (prefers-reduced-motion:reduce) { .architecture-page,.architecture-step,.architecture-arrow,.metric .num { animation:none!important; transition:none!important; } }
''')

# 2) Make login branding modest: keep SIMBA wordmark, simplify the oversized marketing content.
login_html = ROOT / 'templates/login.html'
if login_html.exists():
    s = login_html.read_text(encoding='utf-8')
    original = s
    # Replace the entire copy block only if the expected block exists.
    pattern = re.compile(r'      <div class="brand-copy">.*?      </div>\n      <div class="brand-footer">.*?</div>', re.S)
    replacement = '''      <div class="brand-copy brand-copy-compact">
        <p class="brand-tagline">One platform. Clearer data.</p>
      </div>'''
    s2, n = pattern.subn(replacement, s, count=1)
    if n:
        backup(login_html)
        login_html.write_text(s2, encoding='utf-8')
        print('Simplified SIMBA login branding in templates/login.html')
    else:
        print('Login branding block not matched; left templates/login.html unchanged')
else:
    print('templates/login.html not found; skipped login branding')

# 3) Small tasteful wordmark/tagline treatment on the login page.
login_css = ROOT / 'static/css/login.css'
append_once(login_css, '/* SIMBA compact login brand v1 */', r'''/* SIMBA compact login brand v1 */
.login-brand { gap:11px; font-size:20px; letter-spacing:.12em; font-weight:800; transition:transform .25s ease,opacity .25s ease; }
.login-brand:hover { transform:translateY(-2px); opacity:.96; }
.login-mark { width:42px; height:42px; border-radius:13px; box-shadow:0 7px 18px rgba(225,29,72,.22); animation:simbaMarkFloat 4s ease-in-out infinite; }
.brand-copy-compact { margin-top:clamp(26px,7vh,74px); }
.brand-copy-compact .brand-tagline { max-width:330px; margin:0; font-size:clamp(17px,1.8vw,22px); line-height:1.55; font-weight:550; color:rgba(255,255,255,.86); animation:simbaTaglineIn .7s .1s both; }
@keyframes simbaMarkFloat { 0%,100% {transform:translateY(0)} 50% {transform:translateY(-4px)} }
@keyframes simbaTaglineIn { from {opacity:0; transform:translateY(8px)} to {opacity:1; transform:translateY(0)} }
@media (prefers-reduced-motion:reduce) { .login-mark,.brand-copy-compact .brand-tagline { animation:none!important; } }
''')

# 4) Add an accessible, gentle counter animation to the shared metric component.
js = ROOT / 'static/js/portal.js'
if js.exists():
    text = js.read_text(encoding='utf-8')
    marker = '// SIMBA count-up animation v1'
    if marker in text:
        print('Counter animation already present in static/js/portal.js')
    else:
        old = """  function metric(label, value, hint, key) {
    const el = h('div', { class: 'metric' }, h('div', { class: 'label' }, label), h('div', { class: 'num' }, value), hint ? h('div', { class: 'hint' }, hint) : null);"""
        new = """  // SIMBA count-up animation v1
  function animateMetricValue(node, value) {
    const raw = String(value ?? '');
    const match = raw.match(/^([\\s]*)([\\d,]+)(.*)$/);
    if (!match || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { node.textContent = raw; return; }
    const prefix = match[1], target = Number(match[2].replace(/,/g, '')), suffix = match[3];
    if (!Number.isFinite(target) || target > 1000000000) { node.textContent = raw; return; }
    const start = performance.now(), duration = 650;
    node.textContent = prefix + '0' + suffix;
    function frame(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      node.textContent = prefix + Math.round(target * eased).toLocaleString() + suffix;
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function metric(label, value, hint, key) {
    const num = h('div', { class: 'num' }, '');
    animateMetricValue(num, value);
    const el = h('div', { class: 'metric' }, h('div', { class: 'label' }, label), num, hint ? h('div', { class: 'hint' }, hint) : null);"""
        if old in text:
            backup(js)
            js = text.replace(old, new, 1)
            # append an update animation hook for values updated in-place if metric update uses a rerender
            js = js.replace('  function metric(label, value, hint, key) {', '  function metric(label, value, hint, key) {', 1)
            (ROOT / 'static/js/portal.js').write_text(js, encoding='utf-8')
            print('Added KPI count-up animation to static/js/portal.js')
        else:
            print('Could not locate metric() function; skipped counter JavaScript update')
else:
    print('static/js/portal.js not found; skipped counter animation')

print('\nDone. Backups use the .bak extension. Restart Flask and hard-refresh the browser (Ctrl+F5).')
