"""Score every native-leveled item with setu.leveler and compare with the native levels.
Reports majority baseline, exact, within-one, Spearman, confusion. Thresholds are a-priori (not fitted)."""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from setu.leveler import level, BANDS

ROOT = Path(__file__).resolve().parents[1]


def rank(xs):
    o = sorted(range(len(xs)), key=lambda i: xs[i]); r = [0.0] * len(xs); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and xs[o[j + 1]] == xs[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = rank(a), rank(b); n = len(a); ma, mb = sum(ra) / n, sum(rb) / n
    c = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    d = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** .5
    return c / d if d else float("nan")


def main():
    rows = []
    for d in ("l1-hi_l2-te", "l1-te_l2-hi"):
        for r in json.load(open(ROOT / "data" / d / "rules.json")):
            for it in r["items"]:
                if it.get("level") and it.get("accepted"):
                    rows.append((it["item_id"], it["level"], *level(it["accepted"][0])))
    n = len(rows); nat = [BANDS.index(r[1]) for r in rows]; pred = [BANDS.index(r[2]) for r in rows]
    maj = collections.Counter(nat).most_common(1)[0][1] / n
    out = {"n": n, "majority_baseline": round(maj, 3),
           "exact": round(sum(a == b for a, b in zip(nat, pred)) / n, 3),
           "within_one": round(sum(abs(a - b) <= 1 for a, b in zip(nat, pred)) / n, 3),
           "spearman": round(spearman(nat, [r[3] for r in rows]), 3),
           "confusion": {f"{BANDS[a]}->{BANDS[b]}": c for (a, b), c in sorted(collections.Counter(zip(nat, pred)).items())}}
    print(json.dumps(out, indent=1))
    if "--rows" in sys.argv:
        for r in rows:
            print(r)
    (ROOT / "docs" / "results_leveler.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
