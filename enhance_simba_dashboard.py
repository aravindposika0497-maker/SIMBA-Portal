from pathlib import Path
import shutil
import sys

ROOT = Path.cwd()
required = [ROOT / 'static/css/portal.css', ROOT / 'static/js/portal.js', ROOT / 'templates/index.html']
missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
if missing:
    print('Could not find expected project files: ' + ', '.join(missing))
    print('Run this script from the folder containing templates, static, and wsgi.py.')
    sys.exit(1)

def backup(path):
    target = path.with_suffix(path.suffix + '.before_dashboard_animation.bak')
    if not target.exists():
        shutil.copy2(path, target)

css_path = ROOT / 'static/css/portal.css'
css = css_path.read_text(encoding='utf-8')
marker = '/* SIMBA dashboard motion enhancement v1 */'
if marker not in css:
    backup(css_path)
    css += '''

/* SIMBA dashboard motion enhancement v1 */
:root { --simba-motion-ease: cubic-bezier(.2,.75,.2,1); }
/* Larger, more animated SIMBA branding in the sidebar. */
.side .brand { gap: 13px; padding: 2px 10px 22px; }
.side .brand-mark { width: 44px; height: 44px; border-radius: 13px; box-shadow: 0 7px 22px rgba(215,25,45,.22); animation: simbaMarkFloat 4s ease-in-out infinite; }
.side .brand strong { font-size: 23px; letter-spacing: .045em; line-height: 1.1; background: linear-gradient(100deg,#172033 0%,#d7192d 48%,#172033 90%); background-size: 220% auto; -webkit-background-clip: text; background-clip: text; color: transparent; animation: simbaWordShimmer 7s linear infinite; }
.side .brand small { display:block; margin-top:4px; font-size:11px; letter-spacing:.025em; }
/* Smooth entrance and hover motion for the dashboard and its cards. */
.main { animation: simbaMainReveal .72s var(--simba-motion-ease) both; }
.top { animation: simbaTopDrop .58s var(--simba-motion-ease) both; }
.content { animation: simbaContentRise .7s .08s var(--simba-motion-ease) both; }
.content > * { animation: simbaItemReveal .58s var(--simba-motion-ease) both; }
.content > *:nth-child(2) { animation-delay: .07s; }
.content > *:nth-child(3) { animation-delay: .13s; }
.content > *:nth-child(4) { animation-delay: .19s; }
.content .panel, .content .stat, .content .metric, .content .layer-card, .content .topic-card { transition: transform .24s var(--simba-motion-ease), box-shadow .24s var(--simba-motion-ease), border-color .24s ease; }
.content .panel:hover, .content .stat:hover, .content .metric:hover, .content .layer-card:hover, .content .topic-card:hover { transform: translateY(-3px); box-shadow: 0 14px 34px rgba(28,39,62,.09); border-color: #d5dce8; }
.nav { transition: background .2s ease, transform .2s var(--simba-motion-ease), color .2s ease; }
.nav:hover { transform: translateX(3px); }
.btn, button, a { transition: transform .18s var(--simba-motion-ease), box-shadow .22s ease, background-color .2s ease, border-color .2s ease; }
.btn:hover, .head a:hover { transform: translateY(-1px); }
.live-dot { animation: simbaLivePulse 2s ease-in-out infinite; }
.content.simba-route-enter { animation: simbaContentRise .58s var(--simba-motion-ease) both; }
@keyframes simbaMainReveal { from { opacity:0; filter:blur(3px); } to { opacity:1; filter:blur(0); } }
@keyframes simbaTopDrop { from { opacity:0; transform:translateY(-9px); } to { opacity:1; transform:translateY(0); } }
@keyframes simbaContentRise { from { opacity:0; transform:translateY(14px); } to { opacity:1; transform:translateY(0); } }
@keyframes simbaItemReveal { from { opacity:0; transform:translateY(10px) scale(.995); } to { opacity:1; transform:translateY(0) scale(1); } }
@keyframes simbaMarkFloat { 0%,100% { transform:translateY(0) rotate(0); } 50% { transform:translateY(-3px) rotate(-3deg); } }
@keyframes simbaWordShimmer { 0% { background-position:100% center; } 100% { background-position:-120% center; } }
@keyframes simbaLivePulse { 0%,100% { box-shadow:0 0 0 0 rgba(22,163,74,0); } 50% { box-shadow:0 0 0 4px rgba(22,163,74,.13); } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration:.01ms !important; animation-iteration-count:1 !important; scroll-behavior:auto !important; transition-duration:.01ms !important; } }
'''
    css_path.write_text(css, encoding='utf-8')

js_path = ROOT / 'static/js/portal.js'
js = js_path.read_text(encoding='utf-8')
js_marker = '/* SIMBA route entrance animation v1 */'
if js_marker not in js:
    backup(js_path)
    js += '''

/* SIMBA route entrance animation v1 */
(() => {
  const replay = () => {
    const content = document.querySelector('.content');
    if (!content) return;
    content.classList.remove('simba-route-enter');
    void content.offsetWidth;
    content.classList.add('simba-route-enter');
  };
  window.addEventListener('hashchange', () => window.setTimeout(replay, 40));
  window.addEventListener('DOMContentLoaded', () => window.setTimeout(replay, 80));
})();
'''
    js_path.write_text(js, encoding='utf-8')

print('SIMBA dashboard animations applied.')
print('Updated: static/css/portal.css and static/js/portal.js')
print('Backups created with .before_dashboard_animation.bak suffix.')
print('Restart Flask and hard-refresh the browser with Ctrl+F5.')
