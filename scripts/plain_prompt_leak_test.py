"""Baseline experiment: how often does a PLAIN prompt ("you are a student who doesn't know X")
leak? Runs each item N times against an OpenAI-compatible endpoint (e.g. vLLM serving Gemma 3 12B)
and counts leak-filter reasons. This number is the 'before' in the paper.

  python scripts/plain_prompt_leak_test.py --base-url http://localhost:8000/v1 --model google/gemma-3-12b-it --n 10
  python scripts/plain_prompt_leak_test.py --mock      # offline dry run of the script itself (NOT a result)
"""
import argparse, json, sys, urllib.request
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setu.bank import load_rules, index_items, vocab_for
from setu.leakfilter import check_draft

PROMPT = ("You are a Hindi-speaking student who is learning Telugu. You do not yet know this Telugu grammar point: "
          "{rule}. Write ONE short Telugu sentence for the meaning \"{english}\" the way you, as this student, would write it. "
          "Output only the Telugu sentence.")


def ask(base_url, model, prompt):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.8, "max_tokens": 60}).encode()
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"].strip().splitlines()[0]


def mock(item, k):  # cycles through typical behaviours, just to exercise the script
    return [item.accepted[0], item.planted_error, item.planted_error + " ఎందుకంటే", "నేను ఇంటికి వెళ్తాను"][k % 4]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000/v1"); ap.add_argument("--model", default="google/gemma-3-12b-it")
    ap.add_argument("--n", type=int, default=10); ap.add_argument("--mock", action="store_true")
    ap.add_argument("--out", default="leak_baseline.json")
    a = ap.parse_args()
    rules = load_rules(); idx = index_items(rules)
    state = {r.rule_id: "unknown" for r in rules}
    reasons, ok, total, rows = Counter(), 0, 0, []
    for iid, (rule, item) in idx.items():
        seen = vocab_for(rules, [rule.rule_id])
        for k in range(a.n):
            d = mock(item, k) if a.mock else ask(a.base_url, a.model, PROMPT.format(rule=rule.name, english=item.english))
            dec = check_draft(d, rule, item, rules, seen, state)
            total += 1; ok += dec.ok; reasons.update(dec.reasons)
            rows.append({"item": iid, "draft": d, "ok": dec.ok, "reasons": dec.reasons})
    print(f"drafts: {total}   pass leak filter: {ok} ({100*ok/total:.1f}%)")
    for r, c in reasons.most_common():
        print(f"  {r:22s} {c:4d} ({100*c/total:.1f}%)")
    Path(a.out).write_text(json.dumps({"mock": a.mock, "model": a.model, "total": total, "pass": ok, "reasons": reasons, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")


main()
