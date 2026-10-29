"""Builds app/hosted/setu_app.html (the browser-only version of the tutor) from the template and the rule bank."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
rules = json.loads((ROOT / "data/l1-hi_l2-te/rules.json").read_text(encoding="utf-8"))
t = (ROOT / "app/hosted/setu_app.template.html").read_text(encoding="utf-8")
(ROOT / "app/hosted/setu_app.html").write_text(t.replace("__RULES__", json.dumps(rules, ensure_ascii=False)), encoding="utf-8")
print("ok", len(rules), "rules")
