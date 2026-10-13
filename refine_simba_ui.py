from pathlib import Path
import re, shutil

ROOT = Path(__file__).resolve().parent

def backup(path):
    bak = path.with_suffix(path.suffix + '.bak')
    if not bak.exists():
        shutil.copy2(path, bak)

def read_required(rel):
    p = ROOT / rel
    if not p.exists():
        raise SystemExit(f'Missing {rel}. Put this script in the project root beside wsgi.py.')
    backup(p)
    return p, p.read_text(encoding='utf-8')

# 1) Remove global auth/demo banners from every portal page. Keep truthful data status in the app itself.
p, s = read_required('templates/index.html')
pattern = re.compile(r'\s*\{% if auth_disabled and demo_login_required and demo_mode %\}.*?\{% endif %\}\s*\{% if demo_mode %\}.*?\{% endif %\}\s*', re.S)
s2, n = pattern.subn('\n', s, count=1)
if n:
    print('Removed global authentication/demo warning banners.')
else:
    print('NOTICE: banner block did not match; no banner changes made in templates/index.html.')
p.write_text(s2, encoding='utf-8')

# 2) Remove architecture panel from Overview only; keep the separate Architecture page/navigation if present.
p, js = read_required('static/js/portal.js')
js2 = js
js2, n1 = re.subn(r'\s*const archPanel\s*=\s*panel\([\s\S]*?architectureFlow\(true\)\);\s*', '\n', js2, count=1)
js2, n2 = re.subn(r"h\('div',\s*\{\s*class:\s*'grid g-wide'\s*\},\s*archPanel,\s*layersPanel\s*\)", "h('div', { class: 'grid g-wide' }, layersPanel)", js2, count=1)
# Also handle direct panel declaration inline in overview cards, if present.
if n1 == 0:
    print('NOTICE: architecture panel declaration not matched; inspect Overview renderer in static/js/portal.js.')
if n2 == 0:
    print('NOTICE: architecture overview layout reference not matched; inspect Overview renderer in static/js/portal.js.')
else:
    print('Removed Architecture overview panel from dashboard layout.')
p.write_text(js2, encoding='utf-8')

# 3) Simplify login brand: SIMBA + one tagline, less busy layout.
p, html = read_required('templates/login.html')
html2 = html.replace('<span>SIMBA<span class="brand-slash"> / </span>DATA</span>', '<span>SIMBA</span>')
html2 = html2.replace('One trusted place to explore your data platform, follow the flow, and turn signals into confident decisions.', 'One platform. Clearer data.')
p.write_text(html2, encoding='utf-8')

# 4) Calm, minimal login styling. Overrides existing elaborate effects instead of changing auth/form behavior.
p, css = read_required('static/css/login.css')
css += r'''

/* Refined SIMBA sign-in: minimal brand panel, restrained motion, and quiet surfaces. */
.login-brand-panel{background:linear-gradient(145deg,#181923 0%,#242330 100%);padding:36px clamp(32px,5vw,68px)}
.login-brand-panel:before{opacity:.09;background-size:64px 64px}
.login-brand-panel:after,.brand-orbit,.brand-glow{opacity:.18}
.login-brand{font-size:20px;letter-spacing:.14em;gap:14px}
.login-mark{width:44px;height:44px;border-radius:13px}
.brand-copy{max-width:430px;padding:0;margin:auto 0;animation:copyRise .55s ease-out both}
.brand-copy .eyebrow,.brand-copy h1,.brand-features,.brand-footer{display:none!important}
.brand-tagline{max-width:310px;font-size:16px;line-height:1.75;color:#c9cad4;margin-top:20px}
.login-form-panel{background:#fff;padding:28px clamp(28px,5vw,64px) 20px}
.form-content{max-width:400px;animation:copyRise .45s ease-out both}
.form-icon{width:40px;height:40px;border-radius:12px;box-shadow:none;animation:none;background:#fff3f4}
.form-icon:after{display:none}
.form-content h2{font-size:28px;letter-spacing:-.035em}
.input-wrap{border-radius:9px;box-shadow:none}
.signin-button{border-radius:9px;box-shadow:0 5px 14px rgba(215,25,45,.12)}
.signin-button:hover{transform:translateY(-1px);box-shadow:0 8px 18px rgba(215,25,45,.16)}
.demo-notice{display:none!important}
.form-topline .secure-pill{background:#fff;border-color:#e9ebf0}
@media(max-width:900px){.login-brand-panel{min-height:210px;padding:24px 28px}.brand-copy{padding:0;margin:auto 0}.brand-tagline{margin-top:15px}.login-form-panel{min-height:620px}}
@media(max-width:520px){.login-brand-panel{min-height:170px;padding:22px}.login-brand{font-size:18px}.brand-tagline{font-size:14px}.login-form-panel{min-height:620px;padding:20px 22px}}
'''
p.write_text(css, encoding='utf-8')

print('\nFinished. Backups saved as *.bak beside changed files.')
print('Restart Flask and hard-refresh the browser (Ctrl+F5).')
print('This removes the two banners and Overview architecture panel, and simplifies the login page.')
print('It does not turn simulated figures into live data or alter authentication/environment connections.')
