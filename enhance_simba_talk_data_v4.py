from pathlib import Path
from datetime import datetime
import shutil
import sys

ROOT = Path.cwd()
JS = ROOT / "static" / "js" / "portal.js"
CSS = ROOT / "static" / "css" / "portal.css"

if not JS.exists() or not CSS.exists():
    print("ERROR: Run this script from your existing SIMBAPORTAL folder (the folder containing wsgi.py).")
    print(f"Missing expected file: {JS if not JS.exists() else CSS}")
    sys.exit(1)

js = JS.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")
if "Pages['talk-data']" not in js or ".talk-transcript" not in js or ".talk-prompts" not in js:
    print("ERROR: Your portal files do not match the uploaded SIMBA structure. No files changed.")
    sys.exit(1)

marker = "/* SIMBA TALK TO DATA AESTHETIC V4 */"
if marker in css:
    print("V4 styling is already installed. No files changed.")
    sys.exit(0)

backup = CSS.with_name(f"portal.css.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak")
shutil.copy2(CSS, backup)

styles = r"""
/* SIMBA TALK TO DATA AESTHETIC V4 */
/* Premium workspace treatment scoped to the existing Talk to Data route. */
#view:has(.talk-transcript) {
  --td-ink: #182238;
  --td-muted: #738097;
  --td-red: #d7192d;
  --td-line: #e5eaf2;
}
#view:has(.talk-transcript) > .head {
  min-height: 214px;
  align-items: flex-end;
  margin: 0 0 20px;
  padding: 30px 32px 28px;
  position: relative;
  isolation: isolate;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,.13);
  border-radius: 24px;
  color: #fff;
  background:
    radial-gradient(ellipse at 88% 15%, rgba(255,255,255,.18), transparent 21%),
    radial-gradient(ellipse at 80% 110%, rgba(237,41,67,.55), transparent 38%),
    radial-gradient(ellipse at 54% -20%, rgba(94,117,177,.27), transparent 38%),
    linear-gradient(116deg, #141b2c 0%, #202b43 57%, #551728 100%);
  box-shadow: 0 22px 50px rgba(25,32,52,.18);
}
#view:has(.talk-transcript) > .head::before {
  content: "";
  position: absolute;
  z-index: -1;
  right: -44px;
  top: -98px;
  width: 310px;
  height: 310px;
  border: 1px solid rgba(255,255,255,.13);
  border-radius: 50%;
  box-shadow: 0 0 0 24px rgba(255,255,255,.025), 0 0 0 52px rgba(255,255,255,.02);
}
#view:has(.talk-transcript) > .head::after {
  content: "SIMBA  /  INTELLIGENCE WORKSPACE";
  position: absolute;
  right: 28px;
  bottom: 22px;
  color: rgba(255,255,255,.58);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .17em;
}
#view:has(.talk-transcript) > .head > div:first-child {
  position: relative;
  z-index: 1;
}
#view:has(.talk-transcript) > .head > div:first-child::before {
  content: "✦  YOUR DATA, IN CONVERSATION";
  display: inline-flex;
  align-items: center;
  margin-bottom: 14px;
  padding: 7px 11px;
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 99px;
  color: #fff;
  background: rgba(255,255,255,.075);
  backdrop-filter: blur(8px);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .14em;
}
#view:has(.talk-transcript) > .head h1 {
  margin: 0 0 10px;
  color: #fff;
  font-size: clamp(29px, 3.4vw, 39px);
  line-height: 1.08;
  letter-spacing: -.045em;
}
#view:has(.talk-transcript) > .head p {
  max-width: 600px;
  color: rgba(255,255,255,.75);
  font-size: 13px;
  line-height: 1.8;
}
#view:has(.talk-transcript) .talk-demo-note {
  display: flex !important;
  align-items: center;
  gap: 12px;
  margin: 0 0 20px !important;
  padding: 12px 15px !important;
  border: 1px solid #f0d9aa !important;
  border-radius: 13px !important;
  color: #76541c !important;
  background: linear-gradient(105deg,#fff8e9,#fffdf8) !important;
  box-shadow: 0 5px 16px rgba(105,78,20,.04);
  font-size: 11px !important;
  line-height: 1.65;
}
#view:has(.talk-transcript) .talk-demo-note::before {
  content: "i";
  display: grid;
  place-items: center;
  flex: 0 0 27px;
  height: 27px;
  border-radius: 9px;
  color: #fff;
  background: #a97616;
  font-family: Georgia,serif;
  font-size: 16px;
  font-weight: 700;
}
#view:has(.talk-transcript) .talk-demo-note::after {
  content: "DEMO";
  margin-left: auto;
  padding: 5px 8px;
  border: 1px solid #ecd6a5;
  border-radius: 6px;
  color: #8b641b;
  font-size: 9px;
  font-weight: 850;
  letter-spacing: .13em;
}
#view:has(.talk-transcript) .panel:has(.talk-transcript) {
  overflow: hidden;
  padding: 0;
  border: 1px solid #e1e7f0;
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 16px 44px rgba(23,32,51,.065);
}
#view:has(.talk-transcript) .panel:has(.talk-transcript) > .panelhead {
  margin: 0;
  padding: 20px 24px;
  border-bottom: 1px solid #edf0f5;
  background: linear-gradient(180deg,#fff,#fbfcff);
}
#view:has(.talk-transcript) .panel:has(.talk-transcript) > .panelhead h2 {
  gap: 10px;
  color: #202b40;
  font-size: 15px;
  letter-spacing: -.015em;
}
#view:has(.talk-transcript) .panel:has(.talk-transcript) > .panelhead h2::before {
  content: "S";
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  color: #fff;
  background: linear-gradient(145deg,#f04457,#b20f29);
  box-shadow: 0 6px 14px rgba(215,25,45,.19);
  font-size: 15px;
}
#view:has(.talk-transcript) .panel:has(.talk-transcript) > .panelhead .sub {
  margin-top: 4px;
  color: #8490a4;
  font-size: 11px;
}
#view:has(.talk-transcript) .talk-prompts {
  display: grid !important;
  grid-template-columns: repeat(3,minmax(0,1fr));
  gap: 12px !important;
  margin: 22px 24px 24px !important;
}
#view:has(.talk-transcript) .talk-prompts .btn {
  display: flex;
  align-items: flex-start;
  min-height: 100px;
  padding: 16px !important;
  white-space: normal;
  text-align: left;
  line-height: 1.55;
  border: 1px solid #e4e9f2 !important;
  border-radius: 16px !important;
  color: #2c3850 !important;
  background: linear-gradient(145deg,#fff 0%,#fafbfe 100%) !important;
  box-shadow: 0 5px 14px rgba(23,32,51,.025);
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}
#view:has(.talk-transcript) .talk-prompts .btn::before {
  content: "↗";
  display: grid;
  place-items: center;
  flex: 0 0 30px;
  width: 30px;
  height: 30px;
  margin-right: 11px;
  border: 1px solid #f5d8dd;
  border-radius: 10px;
  color: #c51c32;
  background: linear-gradient(145deg,#fff4f5,#ffe9ed);
  font-weight: 800;
}
#view:has(.talk-transcript) .talk-prompts .btn:hover {
  transform: translateY(-3px);
  border-color: #edb5be !important;
  box-shadow: 0 13px 26px rgba(135,20,43,.075);
}
#view:has(.talk-transcript) .talk-transcript {
  display: flex;
  gap: 17px !important;
  min-height: 320px;
  max-height: 470px !important;
  margin: 0 24px 16px !important;
  padding: 23px !important;
  overflow: auto;
  border: 1px solid #e5eaf3 !important;
  border-radius: 19px !important;
  background:
    radial-gradient(ellipse at 0 0,rgba(229,236,255,.62),transparent 38%),
    linear-gradient(180deg,#fcfdff,#f7f9fc) !important;
  box-shadow: inset 0 1px 0 #fff;
  scroll-behavior: smooth;
}
#view:has(.talk-transcript) .talk-msg {
  max-width: min(80%,700px) !important;
  padding: 15px 17px !important;
  border: 1px solid #e3e9f2 !important;
  border-radius: 17px !important;
  background: rgba(255,255,255,.96) !important;
  box-shadow: 0 7px 20px rgba(24,39,75,.05);
  animation: simbaTalkV4In .22s ease both;
}
#view:has(.talk-transcript) .talk-msg b {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #2a3650;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .025em;
}
#view:has(.talk-transcript) .talk-msg.assistant b::before {
  content: "S";
  display: grid;
  place-items: center;
  width: 25px;
  height: 25px;
  border-radius: 9px;
  color: #fff;
  background: linear-gradient(145deg,#ef4354,#b20f29);
  font-size: 11px;
}
#view:has(.talk-transcript) .talk-msg.user {
  align-self: flex-end;
  border-color: #d6e3ff !important;
  border-bottom-right-radius: 5px !important;
  background: linear-gradient(140deg,#edf4ff,#e6eeff) !important;
}
#view:has(.talk-transcript) .talk-msg.assistant { align-self: flex-start; border-bottom-left-radius: 5px !important; }
#view:has(.talk-transcript) .talk-msg p {
  margin: 9px 0 0 !important;
  color: #4d5a70;
  font-size: 13px;
  line-height: 1.8 !important;
  overflow-wrap: anywhere;
}
#view:has(.talk-transcript) .talk-form {
  display: flex;
  align-items: center;
  gap: 10px !important;
  margin: 0 24px 24px !important;
  padding: 8px;
  border: 1px solid #dfe5ef;
  border-radius: 17px;
  background: #fff;
  box-shadow: 0 9px 27px rgba(24,39,75,.07);
  transition: border-color .2s ease, box-shadow .2s ease;
}
#view:has(.talk-transcript) .talk-form:focus-within {
  border-color: #e9a6b0;
  box-shadow: 0 0 0 4px rgba(215,25,45,.06),0 9px 27px rgba(24,39,75,.07);
}
#view:has(.talk-transcript) .talk-input {
  flex: 1;
  min-width: 0;
  min-height: 45px;
  padding: 12px 14px !important;
  border: 0 !important;
  outline: none;
  color: #202b3e;
  background: transparent;
  font-size: 13px !important;
  box-shadow: none !important;
}
#view:has(.talk-transcript) .talk-input::placeholder { color: #9aa4b5; }
#view:has(.talk-transcript) .talk-form .btn {
  flex: 0 0 auto;
  min-height: 45px;
  padding: 0 22px !important;
  border: 0 !important;
  border-radius: 12px !important;
  color: #fff !important;
  background: linear-gradient(135deg,#e72d45,#b70e2a) !important;
  box-shadow: 0 6px 14px rgba(190,20,45,.2);
  font-weight: 750;
}
#view:has(.talk-transcript) .talk-form .btn:hover { transform: translateY(-1px); box-shadow: 0 10px 20px rgba(190,20,45,.24); }
@keyframes simbaTalkV4In { from { opacity:0; transform:translateY(5px); } to { opacity:1; transform:translateY(0); } }
@media(max-width:900px) {
  #view:has(.talk-transcript) .talk-prompts { grid-template-columns:repeat(2,minmax(0,1fr)); }
}
@media(max-width:640px) {
  #view:has(.talk-transcript) > .head { min-height:0; padding:24px 20px 48px; border-radius:18px; }
  #view:has(.talk-transcript) > .head::after { right:18px; bottom:14px; font-size:8px; }
  #view:has(.talk-transcript) .talk-demo-note { align-items:flex-start; }
  #view:has(.talk-transcript) .talk-demo-note::after { display:none; }
  #view:has(.talk-transcript) .talk-prompts { grid-template-columns:1fr; margin:15px !important; }
  #view:has(.talk-transcript) .talk-prompts .btn { min-height:65px; }
  #view:has(.talk-transcript) .talk-transcript { min-height:240px; margin:0 15px 14px !important; padding:14px !important; }
  #view:has(.talk-transcript) .talk-msg { max-width:95% !important; }
  #view:has(.talk-transcript) .talk-form { margin:0 15px 16px !important; gap:5px !important; padding:5px; }
  #view:has(.talk-transcript) .talk-form .btn { padding:0 14px !important; }
  #view:has(.talk-transcript) .panel:has(.talk-transcript) > .panelhead { padding:16px; }
}
@media(prefers-reduced-motion:reduce) {
  #view:has(.talk-transcript) .talk-msg,
  #view:has(.talk-transcript) .talk-prompts .btn { animation:none!important; transition:none!important; }
  #view:has(.talk-transcript) .talk-transcript { scroll-behavior:auto; }
}
"""

with CSS.open("a", encoding="utf-8", newline="\n") as f:
    f.write("\n\n" + marker + "\n" + styles + "\n")

print("SUCCESS: V4 premium Talk to Data styling added to existing static/css/portal.css.")
print(f"Backup created: {backup.name}")
print("No JavaScript, login, navigation, backend, or project folders were changed.")
print("Refresh with Ctrl+F5. Restart Flask only if your setup requires it.")
