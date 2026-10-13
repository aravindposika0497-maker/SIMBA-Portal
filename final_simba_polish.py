from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent

def backup(p: Path):
    b = p.with_suffix(p.suffix + '.bak')
    if not b.exists():
        shutil.copy2(p, b)

def edit(rel, transform, required=True):
    p = ROOT / rel
    if not p.exists():
        if required:
            print(f'NOT FOUND: {rel} (skip)')
        return False
    backup(p)
    old = p.read_text(encoding='utf-8')
    new = transform(old)
    if new != old:
        p.write_text(new, encoding='utf-8')
        print(f'Updated {rel}')
    else:
        print(f'No text-level changes needed in {rel}; CSS/JS overrides may still apply.')
    return True

# Keep the login brand present, restrained, and readable. Hide the old oversized marketing block.
def login_html(s):
    s = s.replace('<span>SIMBA<span class="brand-slash"> / </span>DATA</span>', '<span>SIMBA</span>')
    s = s.replace('Make data', 'SIMBA')
    s = s.replace('move with', '')
    s = s.replace('purpose.', '')
    s = s.replace('One trusted place to explore your data platform, follow the flow, and turn signals into confident decisions.', 'One platform. Clearer data.')
    return s
edit('templates/login.html', login_html, required=False)

# Login visual polish: moderate brand size, subtle movement, fewer effects.
def login_css(s):
    return s + r'''

/* Final visual polish: understated SIMBA brand and gentle motion. */
.login-brand{font-size:20px!important;letter-spacing:.12em!important;gap:12px!important}
.login-mark{width:42px!important;height:42px!important;border-radius:12px!important}
.brand-copy{padding:0!important;margin:auto 0!important;max-width:360px!important}
.brand-copy .eyebrow,.brand-copy h1,.brand-features,.brand-footer{display:none!important}
.brand-tagline{display:block!important;font-size:15px!important;line-height:1.6!important;margin-top:14px!important;color:#c9cad4!important;max-width:280px!important}
.login-brand-panel{background:linear-gradient(145deg,#21151c,#242330)!important}
.login-brand-panel:before{opacity:.06!important}
.login-brand-panel:after,.brand-orbit,.brand-glow{opacity:.12!important}
.form-content h2{font-size:28px!important}
.demo-notice{display:none!important}
@media(prefers-reduced-motion:no-preference){.login-mark{animation:simbaMarkFloat 4s ease-in-out infinite}.login-brand{animation:simbaBrandIn .65s ease-out both}.signin-button{transition:transform .2s ease,box-shadow .2s ease}}
@keyframes simbaMarkFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}
@keyframes simbaBrandIn{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}
'''
edit('static/css/login.css', login_css, required=False)

# Add robust runtime cleanup for the Data Lake overview card / banners and count-up animation.
# The app uses client-rendered views, so MutationObserver reapplies after navigation/rendering.
def portal_js(s):
    addon = r'''

/* SIMBA polish: remove the Data Lake marketing panel from Overview, hide obsolete demo banners,
   and animate numeric KPI values when views render. Does not alter data or authentication. */
(function simbaFinalPolish(){
  if (window.__simbaFinalPolishInstalled) return;
  window.__simbaFinalPolishInstalled = true;
  const bannerPhrases = [
    'Demo sign-in is enabled',
    'Demo mode. All figures on this page are simulated',
    'SIMULATED DEMO DATA',
    'Authentication is disabled (SIMBA_AUTH_MODE=none)'
  ];
  const clean = () => {
    // Remove banner containers by their distinctive copy, without removing page content.
    document.querySelectorAll('body *').forEach(el => {
      if (el.children.length > 3) return;
      const t = (el.innerText || el.textContent || '').trim();
      if (!t || t.length > 420) return;
      if (bannerPhrases.some(p => t.includes(p))) {
        const target = el.closest('[role="alert"], .alert, .banner, .notice, .warning, .callout') || el;
        target.style.display = 'none';
      }
    });
    // Remove the Overview marketing card headed “What is the Data Lake?” only.
    document.querySelectorAll('h1,h2,h3,h4').forEach(h => {
      if ((h.textContent || '').trim().toLowerCase() === 'what is the data lake?') {
        const card = h.closest('.card, article, section, .panel, .grid-item') || h.parentElement?.parentElement;
        if (card) card.style.display = 'none';
      }
    });
    // Count-up for standalone KPI/stat numbers. Mark each element once per displayed value.
    document.querySelectorAll('h1,h2,h3,h4,[class*="metric"],[class*="stat"],[class*="kpi"],[class*="count"]').forEach(el => {
      if (el.children.length || el.dataset.simbaCounted === '1') return;
      const raw = (el.textContent || '').trim();
      if (!/^\d[\d,]*(?:\.\d+)?%?$/.test(raw)) return;
      const finalValue = Number(raw.replace(/,/g, '').replace('%',''));
      if (!Number.isFinite(finalValue) || finalValue <= 0 || finalValue > 1e9) return;
      el.dataset.simbaCounted = '1';
      const suffix = raw.endsWith('%') ? '%' : '';
      const start = performance.now(), duration = 850;
      const fmt = n => Math.round(n).toLocaleString('en-US') + suffix;
      const tick = now => {
        const p = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = fmt(finalValue * eased);
        if (p < 1) requestAnimationFrame(tick);
      };
      el.classList.add('simba-number-animate');
      requestAnimationFrame(tick);
    });
  };
  const run = () => { try { clean(); } catch (e) { console.debug('SIMBA polish skipped', e); } };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run, {once:true}); else run();
  new MutationObserver(() => run()).observe(document.documentElement, {childList:true,subtree:true});
})();
'''
    if 'window.__simbaFinalPolishInstalled' in s:
        return s
    return s + addon
edit('static/js/portal.js', portal_js, required=False)

# Dashboard animation styles: gentle number pop and card entrance/hover.
def app_css(s):
    return s + r'''

/* Restrained dashboard motion and animated KPI numbers. */
@media (prefers-reduced-motion: no-preference) {
  .simba-number-animate { animation: simbaNumberPop .55s cubic-bezier(.2,.8,.2,1) both; font-variant-numeric: tabular-nums; }
  .card, .panel, .metric-card, .stat-card, .kpi-card { transition: transform .22s ease, box-shadow .22s ease; }
  .metric-card:hover, .stat-card:hover, .kpi-card:hover { transform: translateY(-3px); box-shadow: 0 12px 28px rgba(20,30,55,.08); }
}
@keyframes simbaNumberPop { from { opacity:.35; transform:translateY(5px) scale(.98); } to { opacity:1; transform:translateY(0) scale(1); } }
'''
# Try likely global stylesheets, only edit those that exist.
for rel in ['static/css/portal.css', 'static/css/styles.css', 'static/css/app.css', 'static/css/main.css']:
    edit(rel, app_css, required=False)

print('\nDone. Backups use the .bak extension. Restart Flask and hard-refresh (Ctrl+F5).')
print('If the number animation does not appear, inspect the browser console for JS errors; live values remain unchanged.')
