from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
required = [ROOT / 'templates/login.html', ROOT / 'templates/index.html', ROOT / 'static/css/login.css', ROOT / 'static/css/portal.css', ROOT / 'static/js/portal.js']
missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
if missing:
    raise SystemExit('Run this script from the SIMBA project folder (the folder containing templates/ and static/). Missing: ' + ', '.join(missing))

def edit(path, fn):
    old = path.read_text(encoding='utf-8')
    new = fn(old)
    if old != new:
        path.write_text(new, encoding='utf-8')
        print('Updated', path.relative_to(ROOT))
    else:
        print('No changes needed in', path.relative_to(ROOT))

# Minimal brand panel: SIMBA + one tagline, with animated background retained.
def login_html(s):
    s = re.sub(r'<div class="brand-copy">.*?</div>\s*<div class="brand-footer">',
        '<div class="brand-copy brand-copy-minimal">\n        <h1>SIMBA</h1>\n        <p class="brand-tagline">One platform. Clearer data. Better decisions.</p>\n      </div>\n      <div class="brand-footer">', s, count=1, flags=re.S)
    s = re.sub(r'<a class="login-brand".*?</a>\s*', '', s, count=1, flags=re.S)
    s = s.replace('<span>DEVELOPMENT WORKSPACE</span>', '<span>DATA PLATFORM</span>')
    s = s.replace('<span class="password-note">Demo credentials only</span>', '<span class="password-note">Secure access</span>')
    s = re.sub(r'\s*<div class="demo-notice">.*?</div>\s*', '\n', s, count=1, flags=re.S)
    s = s.replace('Sign in · SIMBA Data', 'Sign in · SIMBA')
    return s
edit(ROOT/'templates/login.html', login_html)

# Environment picker and clean sample-data messaging.
def index_html(s):
    s = s.replace("{{ 'Demo mode · simulated data' if demo_mode else 'Live · Databricks' }}", "{{ 'Sample data · not connected' if demo_mode else 'Databricks connection' }}")
    s = s.replace('<span class="env">{{ environment_label }}</span>', '''<label class="env-picker-label" for="environmentPicker">Environment</label>
          <select class="env-picker" id="environmentPicker" aria-label="Select environment">
            <option value="DEV">DEV</option><option value="UAT">UAT</option><option value="PROD">PROD</option>
          </select>''')
    s = re.sub(r'<div class="banner danger">Demo sign-in is enabled, but this is not production-grade identity management\. Keep this portal on a private network\.</div>',
        '<div class="banner danger">Local sign-in is enabled for this development instance. Keep the portal on a private network.</div>', s)
    s = re.sub(r'<div class="banner warn"><b>Demo mode\.</b> All figures on this page are simulated so the interface can be reviewed\. They are not live platform metrics\. Set SIMBA_DEMO_MODE=false once the Databricks connection is approved and verified\.</div>',
        '<div class="banner warn"><b>Sample data.</b> Figures shown in this instance are illustrative and are not live platform metrics. Verify the Databricks connection before using operational data.</div>', s)
    # Add simple client-side environment selector. It changes the displayed selection only; backend routing is separate.
    marker = '  <script src="{{ url_for(\'static\', filename=\'js/portal.js\') }}" defer></script>'
    addon = '''  <script>
    document.addEventListener('DOMContentLoaded', function () {
      const picker = document.getElementById('environmentPicker');
      if (!picker) return;
      const configured = {{ environment_label|tojson }};
      picker.value = ['DEV','UAT','PROD'].includes(String(configured).toUpperCase()) ? String(configured).toUpperCase() : 'DEV';
      picker.addEventListener('change', function () {
        document.documentElement.dataset.selectedEnvironment = picker.value;
        // UI selection only: wire each environment to its approved backend before using UAT/PROD.
      });
    });
  </script>
'''
    if marker in s and 'id="environmentPicker"' in s and 'data-selected-environment' not in s:
        s = s.replace(marker, addon + marker)
    return s
edit(ROOT/'templates/index.html', index_html)

# Replace user-visible demo labels in the front-end (internal API mode values stay unchanged).
def portal_js(s):
    replacements = {
        "'Demo mode — not connected'": "'Sample data — not connected'",
        "pill('Demo', 'warn')": "pill('Sample data', 'warn')",
        "`Mode: ${state.config.demo_mode ? 'demo' : 'live'} · catalog ${state.config.catalog}`": "`Data source: ${state.config.demo_mode ? 'sample data' : 'live'} · catalog ${state.config.catalog}`",
        "' (demo)'": "' (sample data)'",
    }
    for a,b in replacements.items(): s=s.replace(a,b)
    return s
edit(ROOT/'static/js/portal.js', portal_js)

# Default environment label in backend config and local .env.
config = ROOT/'app/config.py'
if config.exists():
    edit(config, lambda s: s.replace('"NON-PRODUCTION"', '"DEV"'))
env = ROOT/'.env'
if env.exists():
    def env_edit(s):
        s = re.sub(r'^SIMBA_ENVIRONMENT_LABEL=.*$', 'SIMBA_ENVIRONMENT_LABEL=DEV', s, flags=re.M)
        s = s.replace('# LOCAL DEMO ONLY — do not use these demo credentials on a shared/public deployment.', '# LOCAL DEVELOPMENT ONLY — do not use these credentials on a shared/public deployment.')
        return s
    edit(env, env_edit)

# Motion enhancements and clean minimal branding.
css = ROOT/'static/css/login.css'
extra = r'''

/* SIMBA visual refresh: minimal brand copy, richer motion, subtle animated accents. */
.brand-copy-minimal{margin:auto 0;padding:0;animation:simbaReveal .95s cubic-bezier(.16,1,.3,1) both}
.brand-copy-minimal h1{font-size:clamp(64px,9vw,112px);letter-spacing:-.075em;line-height:.95;margin:0 0 18px;background:linear-gradient(100deg,#fff 10%,#ffb6bf 48%,#fff 80%);background-size:220% auto;color:transparent;background-clip:text;-webkit-background-clip:text;animation:simbaShine 7s linear infinite,simbaReveal .95s cubic-bezier(.16,1,.3,1) both}
.brand-copy-minimal .brand-tagline{font-size:clamp(14px,1.5vw,18px);letter-spacing:.01em;color:#d9d9e5;max-width:350px;animation:taglineIn 1s .18s both}
.login-brand-panel{isolation:isolate}
.login-brand-panel:after{z-index:0;background-size:150px 150px,190px 190px,220px 220px,260px 260px;animation:particleDrift 18s linear infinite,particleBlink 5s ease-in-out infinite alternate}
.brand-orbit{z-index:1;box-shadow:0 0 28px rgba(255,105,120,.04)}
.brand-glow{z-index:0;animation:glow 5s ease-in-out infinite alternate,glowDrift 11s ease-in-out infinite alternate}
.login-form-panel{position:relative;overflow:hidden}
.login-form-panel:before{content:"";position:absolute;inset:-40%;pointer-events:none;background:radial-gradient(circle,rgba(215,25,45,.045),transparent 42%);animation:formAura 12s ease-in-out infinite alternate}
.form-content,.form-topline,.login-footer{position:relative;z-index:1}
.input-wrap{transition:transform .28s cubic-bezier(.2,.8,.2,1),border-color .25s,box-shadow .25s}
.input-wrap:focus-within{transform:translateY(-3px) scale(1.01);box-shadow:0 0 0 4px rgba(215,25,45,.075),0 12px 26px rgba(30,25,45,.06)}
.signin-button{transition:transform .25s cubic-bezier(.2,.8,.2,1),box-shadow .25s,filter .25s}
.signin-button:active{transform:translateY(0) scale(.985)}
@keyframes simbaReveal{from{opacity:0;transform:translateY(26px) scale(.97);filter:blur(8px)}to{opacity:1;transform:translateY(0) scale(1);filter:blur(0)}}
@keyframes simbaShine{0%{background-position:200% center}100%{background-position:-20% center}}
@keyframes taglineIn{from{opacity:0;transform:translateY(12px);letter-spacing:.08em}to{opacity:1;transform:translateY(0);letter-spacing:.01em}}
@keyframes particleBlink{from{opacity:.22}to{opacity:.58}}
@keyframes glowDrift{from{transform:translate3d(0,-12px,0) scale(.95)}to{transform:translate3d(-20px,16px,0) scale(1.12)}}
@keyframes formAura{from{transform:translate3d(-2%,0,0) scale(.92)}to{transform:translate3d(3%,2%,0) scale(1.08)}}
@media(prefers-reduced-motion:reduce){.brand-copy-minimal h1,.brand-copy-minimal,.brand-copy-minimal .brand-tagline,.login-form-panel:before{animation:none!important}}
'''
old = css.read_text(encoding='utf-8')
if 'SIMBA visual refresh: minimal brand copy' not in old:
    css.write_text(old + extra, encoding='utf-8')
    print('Updated static/css/login.css')
else: print('No changes needed in static/css/login.css')

# Environment selector styles.
portal_css = ROOT/'static/css/portal.css'
env_css = '''\n/* DEV / UAT / PROD selector */\n.env-picker-label{font-size:10px;color:var(--muted,#778197);font-weight:700;margin-left:4px}.env-picker{appearance:none;border:1px solid var(--line,#e3e7ef);border-radius:9px;background:var(--surface,#fff);color:var(--ink,#202536);font:700 11px/1.2 inherit;padding:8px 28px 8px 10px;cursor:pointer;box-shadow:0 2px 8px rgba(20,30,55,.04);transition:border-color .2s,box-shadow .2s,transform .2s}.env-picker:hover,.env-picker:focus{border-color:#d7192d;box-shadow:0 0 0 3px rgba(215,25,45,.08);outline:none;transform:translateY(-1px)}\n'''
old = portal_css.read_text(encoding='utf-8')
if '/* DEV / UAT / PROD selector */' not in old:
    portal_css.write_text(old + env_css, encoding='utf-8')
    print('Updated static/css/portal.css')
else: print('No changes needed in static/css/portal.css')

print('\nDone. Restart Flask and hard-refresh the browser with Ctrl+F5.')
print('Note: DEV/UAT/PROD currently changes the visible selector only. Configure separate backend URLs/credentials before connecting to UAT or PROD.')
