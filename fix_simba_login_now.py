from pathlib import Path
import re, sys
ROOT = Path(__file__).resolve().parent
required = [ROOT/'templates/login.html', ROOT/'static/css/login.css']
missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
if missing:
    raise SystemExit('ERROR: Run this script from the project root (the folder containing templates/ and static/). Missing: '+', '.join(missing))

p = ROOT/'templates/login.html'
s = p.read_text(encoding='utf-8')
# Replace the entire left brand copy with just SIMBA and one tagline.
pattern = r'<div class="brand-copy">.*?</div>\s*<div class="brand-footer">'
replacement = '''<div class="brand-copy brand-copy-minimal">
        <h1 class="simba-wordmark">SIMBA</h1>
        <p class="brand-tagline">One platform. Clearer data.</p>
      </div>
      <div class="brand-footer">'''
s2, n = re.subn(pattern, replacement, s, count=1, flags=re.S)
if n != 1:
    raise SystemExit('Could not find the expected brand-copy block in templates/login.html. No files changed.')
s2 = re.sub(r'<a class="login-brand".*?</a>\s*', '', s2, count=1, flags=re.S)
s2 = s2.replace('<span>DEVELOPMENT WORKSPACE</span>', '<span>DATA PLATFORM</span>')
s2 = s2.replace('<title>Sign in · SIMBA Data</title>', '<title>Sign in · SIMBA</title>')
s2 = s2.replace('<span class="password-note">Demo credentials only</span>', '<span class="password-note">Secure access</span>')
s2 = re.sub(r'\s*<div class="demo-notice">.*?</div>\s*', '\n', s2, count=1, flags=re.S)
# Cache bust stylesheet so the browser loads updated styles.
s2 = s2.replace("filename='css/login.css') }}\">", "filename='css/login.css') }}?v=20261013-2\">")
p.write_text(s2, encoding='utf-8')

cssp = ROOT/'static/css/login.css'
css = cssp.read_text(encoding='utf-8')
css += r'''

/* SIMBA minimal animated login refresh */
.login-brand-panel{position:relative;isolation:isolate;overflow:hidden;background:radial-gradient(ellipse at 18% 20%,rgba(239,38,66,.34),transparent 42%),linear-gradient(135deg,#35101e 0%,#191827 52%,#111522 100%)}
.login-brand-panel:before{content:"";position:absolute;inset:-35%;z-index:-1;pointer-events:none;background:conic-gradient(from 0deg,transparent 0 68%,rgba(255,78,106,.12) 78%,transparent 86%);animation:simbaOrbit 22s linear infinite}
.login-brand-panel:after{content:"";position:absolute;inset:0;pointer-events:none;background-image:radial-gradient(circle at 15% 20%,rgba(255,112,136,.45) 0 2px,transparent 3px),radial-gradient(circle at 75% 35%,rgba(255,255,255,.2) 0 2px,transparent 3px),radial-gradient(circle at 42% 78%,rgba(255,112,136,.28) 0 2px,transparent 3px);background-size:170px 190px,230px 210px,260px 230px;animation:simbaParticles 16s ease-in-out infinite alternate;opacity:.65}
.brand-copy-minimal{position:relative;z-index:2;margin:auto 0;animation:simbaEnter 1s cubic-bezier(.16,1,.3,1) both}
.brand-copy-minimal .simba-wordmark{margin:0 0 18px;font-size:clamp(76px,10vw,142px);font-weight:900;letter-spacing:-.085em;line-height:.92;color:#fff;background:linear-gradient(100deg,#fff 0%,#ff9aaa 35%,#fff 52%,#ff526e 70%,#fff 100%);background-size:260% auto;background-clip:text;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:simbaShimmer 6s linear infinite,simbaEnter 1s cubic-bezier(.16,1,.3,1) both;filter:drop-shadow(0 8px 28px rgba(239,38,66,.12))}
.brand-copy-minimal .brand-tagline{margin:0;max-width:390px;color:#e3dfe8;font-size:clamp(17px,2vw,23px);line-height:1.55;letter-spacing:.015em;animation:simbaTagline 1.1s .15s both}
.brand-orbit{animation:simbaOrbit 28s linear infinite;opacity:.5}.orbit-two{animation-direction:reverse;animation-duration:36s}.brand-glow{animation:simbaGlow 7s ease-in-out infinite alternate}
.login-form-panel{position:relative;overflow:hidden}.login-form-panel:before{content:"";position:absolute;width:540px;height:540px;right:-300px;top:-250px;border-radius:50%;background:radial-gradient(circle,rgba(231,24,51,.07),transparent 68%);pointer-events:none;animation:formFloat 9s ease-in-out infinite alternate}
.form-content,.form-topline,.login-footer{position:relative;z-index:1}.input-wrap{transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease}.input-wrap:focus-within{transform:translateY(-2px);box-shadow:0 0 0 4px rgba(225,25,48,.08),0 10px 24px rgba(30,25,45,.06)}.signin-button{position:relative;overflow:hidden;transition:transform .22s ease,box-shadow .22s ease,filter .22s ease}.signin-button:before{content:"";position:absolute;inset:0;transform:translateX(-120%);background:linear-gradient(105deg,transparent 25%,rgba(255,255,255,.25) 50%,transparent 75%);transition:transform .65s ease}.signin-button:hover{transform:translateY(-3px);box-shadow:0 16px 34px rgba(225,25,48,.25);filter:saturate(1.1)}.signin-button:hover:before{transform:translateX(120%)}.sso-button{transition:transform .25s ease,box-shadow .25s ease}.sso-button:hover{transform:translateY(-2px);box-shadow:0 10px 25px rgba(25,30,50,.08)}
@keyframes simbaOrbit{to{transform:rotate(360deg)}}@keyframes simbaParticles{0%{transform:translate3d(0,0,0);background-position:0 0,0 0,0 0}100%{transform:translate3d(-12px,18px,0);background-position:80px -60px,-70px 50px,40px 90px}}@keyframes simbaShimmer{to{background-position:-260% center}}@keyframes simbaEnter{from{opacity:0;transform:translateY(28px) scale(.97);filter:blur(7px)}to{opacity:1;transform:translateY(0) scale(1);filter:blur(0)}}@keyframes simbaTagline{from{opacity:0;transform:translateY(14px);letter-spacing:.1em}to{opacity:1;transform:translateY(0);letter-spacing:.015em}}@keyframes simbaGlow{from{opacity:.35;transform:scale(.92)}to{opacity:.8;transform:scale(1.12)}}@keyframes formFloat{from{transform:translate(-20px,0)}to{transform:translate(0,35px)}}
@media(prefers-reduced-motion:reduce){.login-brand-panel:before,.login-brand-panel:after,.brand-copy-minimal,.brand-copy-minimal .simba-wordmark,.brand-copy-minimal .brand-tagline,.brand-orbit,.brand-glow,.login-form-panel:before{animation:none!important}.signin-button,.input-wrap,.sso-button{transition:none!important}}
'''
cssp.write_text(css, encoding='utf-8')

# Cache-bust the shared portal stylesheet too if present.
idx = ROOT/'templates/index.html'
if idx.exists():
    t = idx.read_text(encoding='utf-8')
    t = t.replace("filename='css/portal.css') }}\">", "filename='css/portal.css') }}?v=20261013-2\">")
    # Replace non-production display strings, without pretending the selector wires actual infrastructure.
    t = t.replace('NON-PRODUCTION', 'DEV').replace('Non-production', 'DEV')
    idx.write_text(t, encoding='utf-8')

print('SUCCESS: Login page updated in place.')
print('Left side now shows only SIMBA and one tagline, with additional animations.')
print('Restart Flask and press Ctrl+F5 in the browser to bypass cached CSS.')
