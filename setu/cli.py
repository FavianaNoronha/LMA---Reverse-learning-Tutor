"""Play the tutor in a terminal.

  python -m setu.cli --learner me --mock                       # no model needed (uses bank sentences)
  python -m setu.cli --learner me --base-url http://localhost:11434/v1 --model gemma3:12b

Commands: /new (learn a new rule)  /turn (Raju's sentence)  /none (say there is no mistake)
          /skip N (pretend N days passed)  /status  /quit
"""
import argparse
from .llm import OpenAICompatLLM, MockLLM
from .memory import Store
from .session import Tutor, NO_ERROR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--learner", default="demo"); ap.add_argument("--store", default="runs")
    ap.add_argument("--base-url", default="http://localhost:11434/v1"); ap.add_argument("--model", default="gemma3:12b")
    ap.add_argument("--mock", action="store_true"); ap.add_argument("--no-llm", action="store_true")
    a = ap.parse_args()
    llm = None if a.no_llm else (MockLLM() if a.mock else OpenAICompatLLM(a.base_url, a.model))
    t = Tutor(Store(a.store), llm)
    print(__doc__.split("Commands:")[1].strip())
    lid = a.learner
    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if cmd in ("/quit", "/q"):
            break
        if cmd == "/new":
            r = t.intro(lid)
            if not r:
                print("You have met every rule."); continue
            print(f"\nNEW RULE: {r['title']}\nWhy: {r['why']}\n  ✗ {r['example_wrong']}\n  ✓ {r['example_right']}\n\n{r['task']}  ({r['hindi']})")
        elif cmd == "/turn":
            r = t.turn(lid)
            if r["kind"] == "need_intro":
                print(r["message"], "Type /new."); continue
            print(f"\nRaju: {r['sentence']}\n      {r['ask']}   (meaning: {r['meaning']})\nFix it, or type /none if it's correct.")
        elif cmd.startswith("/skip"):
            n = float(cmd.split()[1]) if len(cmd.split()) > 1 else 3
            t.skip_days(lid, n); print(f"{n:g} days later…")
        elif cmd == "/status":
            for rid, s in t.status(lid)["rules"].items():
                print(f"  {rid}: ready={s['ready']} recall={s['recall']} raju={s['raju']} ✓{s['correct']} ✗{s['wrong']}")
        else:
            r = t.answer(lid, NO_ERROR if cmd == "/none" else cmd)
            print(r.get("error") or f"[{r['verdict']}] {r['message']}")


if __name__ == "__main__":
    main()
