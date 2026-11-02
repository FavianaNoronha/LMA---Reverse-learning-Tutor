"""Before a long Gemma run: is the server up, is the model there, does it answer in Telugu, how slow is it?
Prints a plain-language verdict and an ETA; exit code 0 = go, 1 = fix something first.
  python scripts/gemma_preflight.py --base-url http://localhost:11434/v1 --model gemma3:12b --profile quick
"""
from __future__ import annotations
import argparse, json, re, sys, time, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setu.bank import index_items, load_rules, vocab_for
from setu.classmate import SCHEMA, build_messages
from setu.llm import OpenAICompatLLM, parse_sentence

# worst-case model calls per profile: leak (29 items x N) + baselines (29 x reps x 8) + simulations (rough)
PROFILES = {"quick": dict(leak_n=3, reps=1, sim_n=2, eval_learners=3), "full": dict(leak_n=10, reps=3, sim_n=5, eval_learners=10)}


def calls_for(p):
    return 29 * p["leak_n"] + 29 * p["reps"] * 8 + p["sim_n"] * 3 * 30 + p["eval_learners"] * 24 * 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:11434/v1"); ap.add_argument("--model", default="gemma3:12b")
    ap.add_argument("--profile", default="quick", choices=list(PROFILES)); ap.add_argument("--out", default="docs/results_gemma/preflight.json")
    a = ap.parse_args()
    root = a.base_url.rstrip("/").removesuffix("/v1")
    try:
        tags = json.load(urllib.request.urlopen(root + "/api/tags", timeout=5))
        names = [m["name"] for m in tags.get("models", [])]
    except Exception as e:
        print(f"NO SERVER at {root}: {e}\n  -> open the Ollama app (llama icon in the menu bar), then run this again."); sys.exit(1)
    if not any(n == a.model or n.split(":")[0] == a.model for n in names):
        print(f"MODEL '{a.model}' is not downloaded. Installed: {', '.join(names) or 'none'}\n  -> run:  ollama pull {a.model}"); sys.exit(1)
    rules = load_rules(); idx = index_items(rules); rule, item = idx["HI-TE-001-a"]
    llm = OpenAICompatLLM(a.base_url, a.model); t = time.time()
    try:
        raw = llm.chat(build_messages(item, vocab_for(rules, [rule.rule_id]), False), schema=SCHEMA)
    except Exception as e:
        print(f"The model did not answer: {e}\n  -> if it says 'model requires more system memory', use a smaller one: gemma3:4b"); sys.exit(1)
    lat = time.time() - t; sent = parse_sentence(raw)
    telugu = bool(re.search(r"[ఀ-౿]", sent))
    print(f"model answered in {lat:.1f}s: {sent!r}   Telugu letters: {'yes' if telugu else 'NO'}   JSON/schema ok: {sent != '' }")
    p = PROFILES[a.profile]; n = calls_for(p)
    eta = n * lat / 60
    print(f"profile '{a.profile}': up to ~{n} model calls; at {lat:.1f}s per call that is up to ~{eta:.0f} minutes (a first call is slower; later ones are usually faster).")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"model": a.model, "latency_s": round(lat, 2), "reply": sent, "telugu": telugu, "profile": a.profile, "eta_minutes": round(eta)}, ensure_ascii=False, indent=1), encoding="utf-8")
    if not telugu:
        print("WARNING: the reply has no Telugu letters. The run will still work but will mostly fail the filter; try gemma3:12b."); 
    print("READY")


if __name__ == "__main__":
    main()
