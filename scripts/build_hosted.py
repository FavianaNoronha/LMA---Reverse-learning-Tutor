"""Builds app/hosted/setu_app.html (the browser-only version of the tutor) from the template and the rule bank."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
rules = json.loads((ROOT / "data/l1-hi_l2-te/rules.json").read_text(encoding="utf-8"))
t = (ROOT / "app/hosted/setu_app.template.html").read_text(encoding="utf-8")
import sys, unicodedata
sys.path.insert(0, str(ROOT))
from setu.script import DIFFERENCES, _assigned
tel2deva = {chr(c): chr(c - 0x300) for c in range(0x0C00, 0x0C80) if _assigned(c) and _assigned(c - 0x300)}
def letters(lo, hi):
    return [chr(c) for c in range(lo, hi + 1) if _assigned(c) and chr(c) in tel2deva and unicodedata.name(chr(c)).find("VOCALIC") < 0]
script = {"tel2deva": tel2deva, "differences": DIFFERENCES,
          "vowels": letters(0x0C05, 0x0C14), "consonants": letters(0x0C15, 0x0C39),
          "signs": letters(0x0C3E, 0x0C4C) + ["ం", "ః", "్"]}
t = t.replace("__SCRIPT__", json.dumps(script, ensure_ascii=False))
page = t.replace("__RULES__", json.dumps(rules, ensure_ascii=False))
(ROOT / "app/hosted/setu_app.html").write_text(page, encoding="utf-8")
# GitHub Pages (Settings -> Pages -> Deploy from branch: main, folder /docs) serves docs/index.html as the site.
# The page is a fragment (claude.ai wraps it); for Pages it gets its own document skeleton.
(ROOT / "docs/index.html").write_text("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>"
    "<style>[hidden]{display:none!important}img{max-width:100%}</style></head><body>" + page + "</body></html>", encoding="utf-8")
print("ok", len(rules), "rules")
