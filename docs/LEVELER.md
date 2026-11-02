# Leveler v0 (Hindi and Telugu, A1–B2)

`setu/leveler.py` scores a target-language sentence from length, conjuncts and grammatical markers (case suffixes,
postpositions, ने, negation, continuous, conditional, relative/"because" words). Fixed thresholds 1.5 / 3.0 / 4.5 map
the score to A1–B2. Weights were set a priori, **not fitted** to the native levels. No lexical frequency (IndicCorp not
downloaded), no model. It complements Madhav's `leveler-v0` (L0–L5 across script/vocabulary/word-forms/structure), which
we did not port.

Result against the 49 native-leveled items (`python scripts/level_items.py`, `docs/results_leveler.json`):
exact 0.694 vs majority baseline 0.633; within-one 0.959; Spearman 0.226.

**Honest reading:** barely above "always say A1". The native levels are 78% A1/A2 and mix rule difficulty with sentence
difficulty; 10 of 14 A2 items were called A1. It is not validated and must not gate the planner. Next: an independent
rater on ~50 sentences, then add frequency ranks and fit thresholds with leave-one-rule-out.

Prior art: ReadMe++ (Naous et al., arXiv 2305.14463) has Hindi sentences with CEFR labels (verified); I found no Telugu
CEFR leveler (search not exhaustive).
