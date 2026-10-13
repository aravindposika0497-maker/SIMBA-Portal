from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).resolve().parent
CSS = ROOT / "static" / "css" / "portal.css"
JS = ROOT / "static" / "js" / "portal.js"

if not CSS.exists():
    raise SystemExit(
        "Could not find static/css/portal.css. Put this script in the project root "
        "(the same folder as wsgi.py)."
    )

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = CSS.with_name(f"portal.css.{stamp}.bak")
shutil.copy2(CSS, backup)

css_patch = r"""

/* SIMBA architecture refinement — appended by update_architecture_vertical.py */
.architecture-flow {
  align-items: stretch;
}
.architecture-step.lake {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.architecture-step.lake .medallion {
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
  justify-content: flex-start !important;
  gap: 10px !important;
  width: 100%;
  margin-top: 14px;
}
.architecture-step.lake .medallion > span {
  display: flex !important;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  width: 100% !important;
  min-width: 0;
  min-height: 54px;
  padding: 12px 14px;
  border: 1px solid var(--line, #dfe6f1);
  border-radius: 12px;
  background: #fff;
  color: var(--ink, #182338);
  font-weight: 700;
  text-align: center;
  line-height: 1.3;
  box-shadow: 0 2px 8px rgba(24, 35, 56, .035);
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}
.architecture-step.lake .medallion > span:hover {
  transform: translateY(-2px);
  border-color: #ef3340;
  box-shadow: 0 8px 18px rgba(24, 35, 56, .09);
}
.architecture-step.lake .medallion > span:nth-child(2),
.architecture-step.lake .medallion > span:nth-child(4) {
  display: none !important;
}
/* Keep the lakehouse container tidy and align it with neighboring stages. */
.architecture-step.lake {
  align-self: stretch;
  padding-bottom: 18px;
}
@media (max-width: 900px) {
  .architecture-flow {
    grid-template-columns: minmax(0, 1fr) !important;
  }
  .architecture-flow .architecture-arrow {
    transform: rotate(90deg);
    justify-self: center;
  }
  .architecture-step.lake .medallion {
    max-width: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .architecture-step.lake .medallion > span {
    transition: none;
  }
}
"""

css = CSS.read_text(encoding="utf-8")
marker = "/* SIMBA architecture refinement — appended by update_architecture_vertical.py */"
if marker not in css:
    CSS.write_text(css.rstrip() + "\n\n" + css_patch + "\n", encoding="utf-8")

print("Architecture CSS updated.")
print(f"Backup created: {backup.name}")
print("Bronze, Silver, and Gold are now stacked vertically at equal width.")
print("Restart Flask and refresh the Architecture page with Ctrl+F5.")
