from pathlib import Path
from datetime import datetime
import shutil
import re

ROOT = Path(__file__).resolve().parent
LOGIN_HTML = ROOT / 'templates' / 'login.html'
LOGIN_CSS = ROOT / 'static' / 'css' / 'login.css'
if not LOGIN_HTML.is_file() or not LOGIN_CSS.is_file():
    raise SystemExit('Could not find templates/login.html and static/css/login.css. Put this script next to wsgi.py.')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
for path in (LOGIN_HTML, LOGIN_CSS):
    shutil.copy2(path, path.with_name(path.name + f'.{stamp}.bak'))

html = LOGIN_HTML.read_text(encoding='utf-8')
start = html.find('<section class="login-brand-panel"')
end = html.find('</section>', start)
if start < 0 or end < 0:
    raise SystemExit('Could not identify the login brand panel in templates/login.html.')
section = '''<section class="login-brand-panel simba-minimal-brand" aria-label="SIMBA">
      <div class="brand-orbit orbit-one" aria-hidden="true"></div>
      <div class="brand-orbit orbit-two" aria-hidden="true"></div>
      <div class="brand-glow" aria-hidden="true"></div>
      <a class="login-brand simba-wordmark" href="/login" aria-label="SIMBA home">
        <span class="login-mark">S</span><span class="simba-word">SIMBA</span>
      </a>
      <div class="simba-left-tagline">One platform. Clearer data.</div>
    </section>'''
html = html[:start] + section + html[end + len('</section>'):]
html = re.sub(r'<span class="password-note">.*?</span>', '', html, flags=re.S)
html = re.sub(r'<div class="demo-notice">.*?</div>', '', html, flags=re.S)
LOGIN_HTML.write_text(html, encoding='utf-8')

css = LOGIN_CSS.read_text(encoding='utf-8')
marker = '/* SIMBA minimal left-panel branding patch */'
if marker not in css:
    css += '''\n\n/* SIMBA minimal left-panel branding patch */
.login-brand-panel.simba-minimal-brand {
  position: relative; overflow: hidden; display: flex; flex-direction: column;
  justify-content: center; align-items: flex-start; gap: 14px;
  padding: clamp(32px, 6vw, 76px); min-height: 100%;
  background: radial-gradient(circle at 18% 18%, rgba(239,35,58,.25), transparent 35%),
              linear-gradient(135deg, #25141d 0%, #201c2a 55%, #3b101c 100%);
}
.simba-minimal-brand .login-brand.simba-wordmark {
  position: relative; z-index: 2; display: inline-flex; align-items: center; gap: 13px;
  text-decoration: none; animation: simbaWordmarkIn .75s cubic-bezier(.2,.75,.25,1) both;
}
.simba-minimal-brand .login-mark {
  width: 42px; height: 42px; display: inline-flex; align-items: center; justify-content: center;
  border-radius: 13px; color: #fff; background: linear-gradient(135deg, #f02c43, #c9102b);
  box-shadow: 0 8px 22px rgba(239,35,58,.25); font-size: 20px; font-weight: 800;
}
.simba-minimal-brand .simba-word {
  color: #fff; font-size: clamp(25px, 2.4vw, 34px); line-height: 1.1;
  letter-spacing: .12em; font-weight: 800; animation: simbaWordGlow 4s ease-in-out infinite;
}
.simba-minimal-brand .simba-left-tagline {
  position: relative; z-index: 2; color: rgba(255,255,255,.78);
  font-size: clamp(14px, 1.2vw, 17px); letter-spacing: .015em;
  animation: simbaTaglineIn .9s .12s both;
}
.simba-minimal-brand .brand-orbit { pointer-events: none; opacity: .45; }
@keyframes simbaWordmarkIn { from {opacity:0;transform:translateY(12px)} to {opacity:1;transform:translateY(0)} }
@keyframes simbaTaglineIn { from {opacity:0;transform:translateY(8px)} to {opacity:1;transform:translateY(0)} }
@keyframes simbaWordGlow { 0%,100% {text-shadow:0 0 0 rgba(255,255,255,0)} 50% {text-shadow:0 0 18px rgba(255,255,255,.16)} }
@media (max-width:760px) {
  .login-brand-panel.simba-minimal-brand { min-height:180px; padding:28px; }
  .simba-minimal-brand .simba-word { font-size:26px; }
}
@media (prefers-reduced-motion:reduce) {
  .simba-minimal-brand .login-brand, .simba-minimal-brand .simba-left-tagline,
  .simba-minimal-brand .simba-word { animation:none !important; }
}
'''
    LOGIN_CSS.write_text(css, encoding='utf-8')

print('Updated login page with SIMBA wordmark and one tagline on the left.')
print('Login form, CSRF token, and authentication routes were preserved.')
print(f'Backups created with timestamp: {stamp}')
print('Restart Flask and press Ctrl+F5 in the browser.')
