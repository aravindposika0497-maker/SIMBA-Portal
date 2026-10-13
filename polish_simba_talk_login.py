from pathlib import Path
import sys

root = Path.cwd()
portal_js = root / 'static' / 'js' / 'portal.js'
login_css = root / 'static' / 'css' / 'login.css'
login_html = root / 'templates' / 'login.html'
missing = [str(p.relative_to(root)) for p in (portal_js, login_css, login_html) if not p.exists()]
if missing:
    print('ERROR: Run this script from the existing SIMBA project root (the folder containing wsgi.py).')
    print('Missing: ' + ', '.join(missing))
    sys.exit(1)

js = portal_js.read_text(encoding='utf-8')
if 'SIMBA_TALK_AESTHETIC_POLISH' not in js:
    js += r'''

/* SIMBA_TALK_AESTHETIC_POLISH — visual-only styling for the existing Talk to Data page */
(function () {
  if (document.getElementById('simba-talk-aesthetic-polish')) return;
  const style = document.createElement('style');
  style.id = 'simba-talk-aesthetic-polish';
  style.textContent = `
    .talk-demo-note {
      display:flex !important; align-items:center; gap:10px; max-width:1040px;
      margin:0 auto 18px !important; padding:11px 16px !important;
      border:1px solid #f2d7a0 !important; border-radius:12px !important;
      background:linear-gradient(100deg,#fff8e9,#fffdf8) !important;
      color:#815b1b !important; font-size:12px !important; line-height:1.55;
      box-shadow:0 4px 14px rgba(130,91,27,.05);
    }
    .talk-demo-note:before { content:'✦'; display:grid; place-items:center; flex:0 0 25px; height:25px; border-radius:8px; background:#ffedc4; color:#8a5b06; font-size:14px; }
    .talk-demo-note:after { content:'DEMO'; margin-left:auto; flex:0 0 auto; font-size:9px; letter-spacing:.12em; font-weight:800; opacity:.75; }
    .talk-prompts { display:grid !important; grid-template-columns:repeat(auto-fit,minmax(185px,1fr)); gap:10px !important; margin:16px 0 20px !important; }
    .talk-prompts .btn { display:flex; align-items:center; justify-content:flex-start; gap:10px; min-height:62px; width:100%; padding:13px 14px !important; white-space:normal; text-align:left; line-height:1.4; border:1px solid #e2e7ef !important; border-radius:13px !important; background:#fff !important; color:#26334a !important; box-shadow:0 3px 12px rgba(24,39,75,.035); transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
    .talk-prompts .btn:before { content:'↗'; display:grid; place-items:center; flex:0 0 28px; height:28px; border-radius:9px; background:#eef3ff; color:#4263c7; font-weight:800; }
    .talk-prompts .btn:hover { transform:translateY(-2px); border-color:#b9c9f6 !important; box-shadow:0 9px 22px rgba(43,69,135,.09); }
    .talk-transcript { max-width:100%; min-height:250px; max-height:430px !important; gap:14px !important; padding:22px !important; margin:0 0 14px !important; border:1px solid #e5eaf2 !important; border-radius:18px !important; background:radial-gradient(ellipse at top left,rgba(230,237,255,.58),transparent 42%),linear-gradient(180deg,#fbfcff,#f7f9fc) !important; box-shadow:inset 0 1px 0 #fff; scroll-behavior:smooth; }
    .talk-msg { position:relative; max-width:min(82%,720px) !important; padding:14px 16px !important; border:1px solid #e4e9f1 !important; border-radius:15px !important; background:#fff !important; box-shadow:0 5px 16px rgba(24,39,75,.045); color:#283348; }
    .talk-msg b { display:flex; align-items:center; gap:7px; color:#26334a; font-size:12px; letter-spacing:.01em; }
    .talk-msg.assistant b:before { content:'S'; display:grid; place-items:center; width:23px; height:23px; border-radius:8px; background:linear-gradient(145deg,#e52b42,#b60e28); color:white; font-size:11px; box-shadow:0 3px 8px rgba(215,25,45,.18); }
    .talk-msg.user { align-self:flex-end; border-color:#d3e1ff !important; border-bottom-right-radius:5px !important; background:linear-gradient(135deg,#edf4ff,#e7efff) !important; }
    .talk-msg.assistant { align-self:flex-start; border-bottom-left-radius:5px !important; }
    .talk-msg p { margin:8px 0 0 !important; font-size:13px; line-height:1.7 !important; color:#4d596d; }
    .talk-form { position:relative; display:flex; align-items:center; gap:10px !important; padding:8px; border:1px solid #dfe5ee; border-radius:15px; background:#fff; box-shadow:0 8px 24px rgba(24,39,75,.07); }
    .talk-input { width:100%; padding:13px 14px !important; border:0 !important; outline:none; background:transparent; color:#202b3e; font-size:13px !important; box-shadow:none !important; }
    .talk-input:focus { outline:none; }
    .talk-form .btn { flex:0 0 auto; min-height:42px; padding:0 19px !important; border:0 !important; border-radius:10px !important; background:linear-gradient(135deg,#dc243b,#b50d29) !important; color:#fff !important; box-shadow:0 5px 12px rgba(190,20,45,.2); }
    .talk-form .btn:hover { filter:brightness(1.05); transform:translateY(-1px); }
    @media(max-width:640px) { .talk-transcript{padding:13px!important;min-height:220px}.talk-msg{max-width:94%!important}.talk-prompts{grid-template-columns:1fr}.talk-demo-note{align-items:flex-start}.talk-demo-note:after{display:none}.talk-form{gap:5px!important;padding:5px}.talk-form .btn{padding:0 12px!important} }
    @media(prefers-reduced-motion:reduce) { .talk-prompts .btn,.talk-transcript{transition:none!important;scroll-behavior:auto!important} }
  `;
  document.head.appendChild(style);
})();
'''
    portal_js.write_text(js, encoding='utf-8')
    print('Updated Talk to Data styling in static/js/portal.js')
else:
    print('Talk to Data styling polish already exists in static/js/portal.js')

css = login_css.read_text(encoding='utf-8')
if 'SIMBA_LOGIN_LOGO_TOP_POLISH' not in css:
    css += r'''

/* SIMBA_LOGIN_LOGO_TOP_POLISH — keep the supplied SIMBA logo at the top of the login brand panel */
.login-brand-panel.simba-minimal-brand { position:relative; }
.login-brand-panel.simba-minimal-brand .login-simba-logo {
  position:absolute !important; top:28px !important; right:clamp(24px,4vw,58px) !important;
  z-index:5 !important; width:clamp(108px,11vw,148px) !important; height:auto !important;
  margin:0 !important; padding:5px !important; border-radius:9px !important;
  background:#fff !important; box-shadow:0 8px 26px rgba(0,0,0,.18) !important;
}
@media(max-width:760px) {
  .login-brand-panel.simba-minimal-brand .login-simba-logo { top:18px !important; right:20px !important; width:94px !important; }
  .login-brand-panel.simba-minimal-brand .login-brand.simba-wordmark { max-width:calc(100% - 115px); }
}
'''
    login_css.write_text(css, encoding='utf-8')
    print('Moved the supplied SIMBA logo visually to the top of the login page brand panel via static/css/login.css')
else:
    print('Login logo top styling already exists in static/css/login.css')

print('\nDONE — edited only existing files; no new project folder created.')
print('Restart Flask and refresh the browser with Ctrl+F5 to clear cached CSS/JS.')
