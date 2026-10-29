# Final submission checklist (LMA course)

The course asks every group to answer the four **intake questions** for its system, in writing, one line each.
Keep these answers true as the system changes, and back each one with evidence from the code or logs.

| # | Question | Our answer (keep updated) | Evidence we must show |
|---|----------|---------------------------|-----------------------|
| 1 | Which single part of your system genuinely needs the model to choose the next step? | None of the control flow: the planner, leak filter and checker are rules; the model only writes Raju's sentence (later the coach hint and Sravya's open conversation), so it is a workflow with a model inside, not an agent. | `setu/session.py`: every branch is decided by rules; `setu/classmate.py`: the model only rewrites a bank sentence. If we ever let the model pick the next step (e.g. Sravya choosing where a scene goes), name it here. |
| 2 | What does one full episode cost you, in model calls? | ~1 call per exchange for Raju (max 3 if drafts are rejected) + 1 for the coach once it uses the model; a 12-exchange session ≈ 12–24 calls typical, ≤ 48 worst. | `Tutor.status()` reports `turns`, `model_calls`, `calls_per_turn`; report the measured mean and max from the pilot and the Gemma baseline run. |
| 3 | Name one tool your design assumes and you do not yet have. | A Telugu morphological analyser (LTRC / Stanza) wired into the checker; today the checker uses item-level patterns. | Either integrate it and show the checker results, or list it as a limitation with its effect (checker can't judge unseen word forms → more `unsure`). |
| 4 | What is the worst action your agent can take, and who would notice it? | Marking a wrong Telugu fix as correct, or planting a "mistake" that is actually correct Telugu, so the learner learns wrong Telugu; the learner can't notice, only native-speaker review of the rule bank and teachers' blind marking would. | Checker false-accept rate on the held-out test set (Table 9 target: catch ≥ 90% of wrong fixes); every rule `native_checked` before learners; teacher queue log. |

Also required by our own plan for submission: paper (v8+), repo with tests passing, plain-language explainer,
Gemma leak baseline numbers, Table 9 metrics filled in, consent forms, interview notes.
