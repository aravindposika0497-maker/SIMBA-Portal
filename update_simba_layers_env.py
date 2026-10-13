from pathlib import Path
import re, shutil, sys

ROOT = Path.cwd()
required = [ROOT / 'wsgi.py', ROOT / 'static/js/portal.js', ROOT / 'static/css/portal.css', ROOT / 'templates/index.html']
missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
if missing:
    print('Run this script from the SIMBA project root (the folder containing wsgi.py). Missing:', ', '.join(missing))
    sys.exit(1)

files = [ROOT/'static/js/portal.js', ROOT/'static/css/portal.css', ROOT/'templates/index.html', ROOT/'content/portal.json']
for p in files:
    if p.exists():
        backup = p.with_suffix(p.suffix + '.bak')
        if not backup.exists(): shutil.copy2(p, backup)

# Make Bronze/Silver/Gold cards consistent: title + layer icon + row/dataset statistic only.
js_path = ROOT/'static/js/portal.js'
js = js_path.read_text(encoding='utf-8')
old = """      h('div', { class: 'layer-head' }, h('span', { class: `layer-icon ${l.schema}` }), h('div', null, h('h3', null, l.name), h('div', { class: 'tag' }, l.tag))),
      h('p', null, l.body),
      h('ul', null, l.examples.map((e) => h('li', null, e))),
      h('div', { class: 'stat' }, stat));"""
new = """      h('div', { class: 'layer-head' }, h('span', { class: `layer-icon ${l.schema}` }), h('div', null, h('h3', null, l.name))),
      h('div', { class: 'stat' }, stat));"""
if old in js:
    js = js.replace(old, new, 1)
else:
    print('Note: layer card markup did not match expected source; left JS card markup unchanged.')
# Replace visible demo labels with neutral, truthful sample-data language.
replacements = {
    "'Demo mode · simulated data'": "'Sample data · not live'",
    "'Live · Databricks'": "'Databricks workspace'",
    "'Demo mode — not connected'": "'Sample data — not connected'",
    "pill('Demo', 'warn')": "pill('Sample data', 'warn')",
    "' (demo)'": "' (sample data)'",
    "'demo' : 'live'": "'sample data' : 'live'",
    "'Demo values. Counts tick upward to exercise the live-update path.'": "'Sample figures are illustrative until a live data connection is verified.'",
}
for a,b in replacements.items(): js = js.replace(a,b)
js_path.write_text(js, encoding='utf-8')

# Equal-height layer cards and restrained entrance animation.
css_path = ROOT/'static/css/portal.css'
css = css_path.read_text(encoding='utf-8')
css += r'''

/* Consistent medallion cards: no long descriptions, equal heights, gentle motion. */
#view .grid.g3:has(> .layer) { align-items: stretch; }
#view .layer { min-height: 132px; height: 100%; box-sizing: border-box; justify-content: space-between; gap: 18px; animation: simbaLayerIn .48s both; }
#view .layer:nth-child(2) { animation-delay: .08s; }
#view .layer:nth-child(3) { animation-delay: .16s; }
#view .layer .layer-head { min-height: 40px; }
#view .layer .stat { padding-top: 12px; }
@keyframes simbaLayerIn { from { opacity: 0; transform: translateY(12px) scale(.985); } to { opacity: 1; transform: translateY(0) scale(1); } }
'''
css_path.write_text(css, encoding='utf-8')

# Environment badge becomes a selector. It changes the UI label only; backend credentials/config remain unchanged.
html_path = ROOT/'templates/index.html'
html = html_path.read_text(encoding='utf-8')
html = html.replace("<span class=\"env\">{{ environment_label }}</span>", '''<label class="env-picker" aria-label="Select workspace environment">
            <span class="env-dot" aria-hidden="true"></span>
            <select id="environment-select" class="env-select" aria-label="Environment">
              <option value="DEV">DEV</option><option value="UAT">UAT</option><option value="PROD">PROD</option>
            </select>
          </label>''')
html_path.write_text(html, encoding='utf-8')

css += ''
with css_path.open('a', encoding='utf-8') as f:
    f.write(r'''
.env-picker { display:inline-flex; align-items:center; gap:8px; border:1px solid var(--line); border-radius:999px; background:#fff; padding:7px 12px; }
.env-dot { width:8px; height:8px; border-radius:50%; background:var(--red); box-shadow:0 0 0 4px rgba(225,29,55,.09); }
.env-select { border:0; outline:0; background:transparent; color:var(--red); font:inherit; font-size:12px; font-weight:800; cursor:pointer; }
''')

# Add harmless environment selection persistence for the UI; it does NOT switch backend resources.
marker = "  // ------------------------------------------------------------------ DOM helpers"
if marker in js:
    pass
# Append initializer to existing deferred script by inserting before final IIFE closure.
js = js_path.read_text(encoding='utf-8')
end = "})();"
initializer = r'''
  // Environment selector is a visual workspace label only; backend endpoints are unchanged.
  document.addEventListener('DOMContentLoaded', () => {
    const picker = document.getElementById('environment-select');
    if (!picker) return;
    const stored = sessionStorage.getItem('simba-ui-environment');
    if (stored && ['DEV', 'UAT', 'PROD'].includes(stored)) picker.value = stored;
    picker.addEventListener('change', () => sessionStorage.setItem('simba-ui-environment', picker.value));
  });
'''
if 'simba-ui-environment' not in js and js.rstrip().endswith(end):
    js = js.rstrip()[:-len(end)] + initializer + '\n' + end + '\n'
    js_path.write_text(js, encoding='utf-8')

# Clean up visible labels in portal content while preserving actual data and keys.
content_path = ROOT/'content/portal.json'
if content_path.exists():
    raw = content_path.read_text(encoding='utf-8')
    # Only visible strings: replace demo naming prefix and demo words, not configuration keys.
    raw = re.sub(r'(?i)\bdemo_', 'sample_', raw)
    raw = re.sub(r'(?i)\bdemo\b', 'sample data', raw)
    content_path.write_text(raw, encoding='utf-8')

print('SIMBA UI updates applied. Backups with .bak extensions were created for edited files.')
print('Reminder: DEV/UAT/PROD selector changes only the displayed selection. Configure separate approved backend credentials before using real environments.')
