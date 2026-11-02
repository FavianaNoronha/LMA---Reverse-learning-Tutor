"""Real-model baselines for Raju: how often does each way of using the model produce a sentence that passes the
leak filter, and what does it cost? Four methods on the same items, rule unknown, learner has seen the rule's words:

  plain_no_reference  the model must invent the learner mistake itself (the 'before' number)
  prompt_only         the model rewrites the bank sentence once; we take what it says (the filter only measures)
  resample            up to 3 drafts, no feedback, keep the first that passes the filter (setu/classmate.py)
  tool                up to 3 model calls, the model reads the filter's reasons and revises (setu/agent.py)

Lessons built in (from the team's first run, which was spoiled by an API quota):
  * every model error is recorded; a case with any error is EXCLUDED from the rates and counted separately,
    so a broken run can never look like a result;
  * the run aborts early if the first calls all fail (server not running, wrong model name);
  * the safety invariant is checked on real output: a sentence shown by resample/tool must pass the filter again.

  python scripts/gemma_baselines.py --base-url http://localhost:11434/v1 --model gemma3:12b --reps 1
  python scripts/gemma_baselines.py --mock        # dry run of the harness itself (NOT a result)
"""
from __future__ import annotations
import argparse, json, statistics, sys, time
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setu.agent import raju_agent_turn
from setu.bank import index_items, load_rules, vocab_for
from setu.classmate import SCHEMA, build_messages, raju_turn
from setu.leakfilter import check_draft
from setu.llm import AgentMockLLM, MockLLM, OpenAICompatLLM, parse_sentence
from scripts.plain_prompt_leak_test import PROMPT as PLAIN_PROMPT

METHODS = ("plain_no_reference", "prompt_only", "resample", "tool")
LEAK_REASONS = {"ANSWER_LEAK", "UNKNOWN_RULE_CORRECT"}


class Recorder:
    """Wraps any LLM: counts calls, times them, keeps every error (never swallows one silently)."""
    def __init__(self, llm):
        self.llm, self.model = llm, getattr(llm, "model", "?")
        self.calls, self.errors, self.latencies = 0, [], []

    def chat(self, messages, temperature=0.8, max_tokens=120, schema=None):
        t = time.time(); self.calls += 1
        try:
            out = self.llm.chat(messages, temperature=temperature, max_tokens=max_tokens, schema=schema)
        except Exception as e:                      # recorded, then re-raised for the caller's own handling
            self.errors.append(f"{type(e).__name__}: {e}"[:200]); raise
        self.latencies.append(time.time() - t); return out


class HarnessMock:
    """Offline stand-in that answers all four prompt styles, so the harness itself can be tested (NOT a result)."""
    model = "harness-mock"

    def __init__(self):
        self.agent, self.n = AgentMockLLM(leaky_every=3), 0

    def chat(self, messages, temperature=0.8, max_tokens=120, schema=None):
        self.n += 1
        if messages[0]["role"] == "system" and "check_classmate_sentence" in messages[0]["content"]:
            return self.agent.chat(messages, temperature, max_tokens, schema)
        user = messages[-1]["content"]
        if "Reference sentence" in user:
            ref = user.split("): ", 1)[1].split("\n", 1)[0]
            return json.dumps({"sentence": ref if self.n % 4 else "ఇది పుస్తకం ఎందుకంటే నియమం"}, ensure_ascii=False)
        return "ఇది పుస్తకం" if self.n % 2 else "నేను ఇంటికి వెళ్తాను"


class Aborted(RuntimeError):
    pass


def run_case(method, rec, rule, item, rules, idx, seen, state):
    calls0, err0, lat0 = rec.calls, len(rec.errors), len(rec.latencies)
    row = {"method": method, "item": item.item_id, "rule": rule.rule_id}
    if method == "plain_no_reference":
        d = ""
        try:
            d = rec.chat([{"role": "user", "content": PLAIN_PROMPT.format(rule=rule.name, english=item.english)}], max_tokens=60).strip().splitlines()[0]
        except Exception:
            pass
        dec = check_draft(d, rule, item, rules, seen, state)
        row.update(shown=d, ok=dec.ok, first_ok=dec.ok, source="model", reasons=dec.reasons)
    elif method == "prompt_only":
        d = ""
        try:
            d = parse_sentence(rec.chat(build_messages(item, seen, False), schema=SCHEMA))
        except Exception:
            pass
        dec = check_draft(d, rule, item, rules, seen, state)
        row.update(shown=d, ok=dec.ok, first_ok=dec.ok, source="model", reasons=dec.reasons)
    else:
        turn = (raju_turn(rec, rule, item, rules, seen, state, "bench") if method == "resample"
                else raju_agent_turn(rec, rule, item, rules, idx, seen, state, "bench"))
        first = turn.rejected[0]["reasons"] if turn.rejected else []
        shown_ok = check_draft(turn.draft, rule, item, rules, seen, state).ok
        row.update(shown=turn.draft, ok=turn.source == "llm", first_ok=not turn.rejected, source=turn.source,
                   reasons=first, rejected=[r["reasons"] for r in turn.rejected], shown_passes_filter=shown_ok)
    row.update(calls=rec.calls - calls0, errors=rec.errors[err0:], latency_s=round(sum(rec.latencies[lat0:]), 2))
    return row


def summarise(rows):
    out = {}
    for m in METHODS:
        allr = [r for r in rows if r["method"] == m]
        good = [r for r in allr if not r["errors"]]
        n = len(good)
        if not n:
            out[m] = {"n": 0, "excluded_error_cases": len(allr)}; continue
        reasons = Counter(x for r in good for x in r["reasons"])
        out[m] = {"n": n, "excluded_error_cases": len(allr) - n,
                  "valid_rate": round(sum(r["ok"] for r in good) / n, 3),
                  "first_draft_pass_rate": round(sum(r["first_ok"] for r in good) / n, 3),
                  "fallback_rate": round(sum(r["source"] == "bank" for r in good) / n, 3),
                  "leak_rate": round(sum(bool(LEAK_REASONS & set(r["reasons"])) for r in good) / n, 3),
                  "oov_rate": round(sum("OOV" in r["reasons"] for r in good) / n, 3),
                  "not_one_error_rate": round(sum("NOT_ONE_ERROR" in r["reasons"] for r in good) / n, 3),
                  "no_tool_call_rate": round(sum("NO_TOOL_CALL" in x for r in good for x in r.get("rejected", [])) / n, 3),
                  "calls_per_case": round(statistics.mean(r["calls"] for r in good), 2),
                  "median_latency_s": round(statistics.median(r["latency_s"] for r in good), 2),
                  "first_draft_reasons": dict(reasons),
                  "shown_fails_filter": sum(1 for r in good if r.get("shown_passes_filter") is False)}
    return out


def run(llm, reps=1, methods=METHODS, items_limit=None, log=print, abort_after=6):
    rules = load_rules(); idx = index_items(rules); state = {r.rule_id: "unknown" for r in rules}
    rec = Recorder(llm); rows = []
    todo = [(iid, rule, item) for iid, (rule, item) in idx.items()][: items_limit or None]
    ok_replies = 0
    for rep in range(reps):
        for iid, rule, item in todo:
            seen = vocab_for(rules, [rule.rule_id])
            for m in methods:
                row = run_case(m, rec, rule, item, rules, idx, seen, state); row["rep"] = rep; rows.append(row)
                ok_replies += 0 if row["errors"] else 1
                if not ok_replies and len(rec.errors) >= abort_after:
                    raise Aborted(f"first {len(rec.errors)} model calls all failed: {rec.errors[0]}")
            log(f"  rep {rep+1}/{reps}  {iid}  done ({len(rows)} cases, {len(rec.errors)} errors)")
    return rows, rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:11434/v1"); ap.add_argument("--model", default="gemma3:12b")
    ap.add_argument("--reps", type=int, default=1); ap.add_argument("--items", type=int, default=0, help="limit items (0 = all 29)")
    ap.add_argument("--mock", action="store_true"); ap.add_argument("--out", default="docs/results_gemma/baselines.json")
    a = ap.parse_args()
    llm = HarnessMock() if a.mock else OpenAICompatLLM(a.base_url, a.model)
    t0 = time.time(); status = "mock" if a.mock else "run"; rows = []
    try:
        rows, rec = run(llm, a.reps, items_limit=a.items)
    except Aborted as e:
        status = "aborted"; print("ABORTED:", e); rows = []; rec = None
    res = {"status": status, "model": getattr(llm, "model", a.model), "endpoint": None if a.mock else a.base_url, "hosted": False,
           "reps": a.reps, "cases_per_method": len({r["item"] for r in rows}) * a.reps, "seconds": round(time.time() - t0),
           "completion_tokens": getattr(llm, "completion_tokens", 0), "methods": summarise(rows) if rows else {},
           "all_errors": sorted(set(e for r in rows for e in r["errors"]))[:10], "rows": rows}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for m, v in res["methods"].items():
        print(f"{m:20s} n={v['n']:3d} valid={v.get('valid_rate')} first_draft={v.get('first_draft_pass_rate')} fallback={v.get('fallback_rate')} "
              f"leak={v.get('leak_rate')} calls={v.get('calls_per_case')} lat={v.get('median_latency_s')}s excluded={v['excluded_error_cases']}")
    if status == "aborted":
        sys.exit(2)


if __name__ == "__main__":
    main()
