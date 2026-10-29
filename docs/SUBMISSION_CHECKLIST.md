# Final submission checklist (LMA course)

The course asks every group to answer the four **intake questions** for its system, in writing, one line each.
Keep these answers true as the system changes, and back each one with evidence from the code or logs.

| # | Question | Our answer (keep updated) | Evidence we must show |
|---|----------|---------------------------|-----------------------|
| 1 | Which single part of your system genuinely needs the model to choose the next step? | Only Raju's drafting loop: the model writes a draft, calls `check_classmate_sentence`, reads the reasons and chooses how to revise (≤ 3 calls, then the bank sentence). Everything else (planner, checker, memory, forgetting) is rules. Later: Sravya choosing where a scene goes. | `setu/agent.py` (loop), `tests/test_agent.py`; the demo app's inside panel shows each tool call. `setu/session.py`: every other branch is rules. |
| 2 | What does one full episode cost you, in model calls? | ~1 call per exchange for Raju in agent mode when the first draft passes the tool (max 3 if he revises; the harness submits a tool-approved sentence without an extra call) + 1 for the coach once it uses the model; a 12-exchange session ≈ 12–24 calls typical, ≤ 48 worst. | `Tutor.status()` reports `turns`, `model_calls`, `calls_per_turn`; report the measured mean and max from the pilot and the Gemma baseline run. |
| 3 | Name one tool your design assumes and you do not yet have. | A Telugu morphological analyser (LTRC / Stanza) wired into the checker; today the checker uses item-level patterns. | Either integrate it and show the checker results, or list it as a limitation with its effect (checker can't judge unseen word forms → more `unsure`). |
| 4 | What is the worst action your agent can take, and who would notice it? | Marking a wrong Telugu fix as correct, or planting a "mistake" that is actually correct Telugu, so the learner learns wrong Telugu; the learner can't notice, only native-speaker review of the rule bank and teachers' blind marking would. | Checker false-accept rate on the held-out test set (Table 9 target: catch ≥ 90% of wrong fixes); every rule `native_checked` before learners; teacher queue log. |

Also required by our own plan for submission: paper (v8+), repo with tests passing, plain-language explainer,
Gemma leak baseline numbers, Table 9 metrics filled in, consent forms, interview notes.

## Activity 3: schema for one of our tools

Tool: `check_classmate_sentence` — implemented in `setu/tools.py`, tested in `tests/test_tools.py`
(the leak filter exposed as a function the model calls on each draft before it is shown).

- **When to use:** on every draft sentence Raju wants to show the learner.
- **When not to:** to mark the learner's own answer (that's the checker), or to translate or explain.
- **item_id** — string, pattern `^(HI-TE|TE-HI)-[0-9]{3}-[a-z]$`, e.g. `HI-TE-002-a`.
  Likely wrong values: the rule id `HI-TE-002`, or the English meaning "This is a book."
- **sentence** — string, one sentence in Telugu script, 1–120 chars.
  Likely wrong values: romanized `idi pustakam undi`, the sentence plus an English gloss, Hindi text, or two sentences.
- **Exact error strings** (first invalid argument only):
  - `ERROR invalid_argument item_id: "HI-TE-002" is a rule id; pass an item id like "HI-TE-002-a".`
  - `ERROR invalid_argument item_id: "<v>" does not match HI-TE-NNN-x (example: HI-TE-002-a).`
  - `ERROR invalid_argument item_id: "<v>" is not in the rule bank.`
  - `ERROR invalid_argument sentence: contains Latin letters; pass Telugu script only, no romanization or English.`
  - `ERROR invalid_argument sentence: no Telugu characters found; pass the sentence in Telugu script.`
  - `ERROR invalid_argument sentence: more than one sentence or line; pass exactly one sentence.`
  - `ERROR invalid_argument sentence: empty; pass one Telugu sentence.` / `... longer than 120 characters; pass one short sentence.`
- **Success return:** `{"ok": true|false, "reasons": [OOV | NOT_ONE_ERROR | UNKNOWN_RULE_CORRECT | ANSWER_LEAK | EXPLANATION]}`

## Course "key messages" → where they show up in SETU

| Key message | In our system | Status |
|---|---|---|
| Agents combine **reasoning, tools and dynamic learning** for goal-oriented tasks | Raju's goal: one valid planted-error sentence. He drafts (reasoning), calls `check_classmate_sentence` (tool), revises from the reasons. **Dynamic learning:** Raju's knowledge changes per learner (taught → forgotten) and Sravya adapts to the learner's seen words | **Built:** Raju agent loop + tool (`setu/agent.py`, 7 tests), shown live in the demo app. Sravya to build |
| Tools = **Extensions, Functions, Data Stores** | **Functions:** `check_classmate_sentence`, `check_level`, `check_hint_has_no_answer`. **Data stores:** rule bank (`rules.json`), learner record (seen words, rule memory). **Extensions** (external APIs): speech (IndicConformer ASR / Indic Parler-TTS), Telugu analyser | Functions/data stores partly built; extensions planned |
| Needs **robust orchestration and iterative refinement** | `setu/session.py` orchestrates; bounded loops (≤ 3 drafts, then bank fallback); only the checker writes memory; every turn logs model + prompt + rule version, calls per turn | Built (v0) |
| A **rapidly evolving** field | Related work cites 2025–26 papers on simulated/weak students (Yuan; Do, Sonkar & Sachan; Apartsin; StudentSim; Song unlearning) | In paper v8 |

## Prompt injection

Untrusted text in SETU: what learners type (answers, explanations, chat with Sravya), learner writing that teachers upload, and anything a model writes.

1. **No authority in the model.** Models only produce text. They cannot mark answers, change learner or Raju state, or call any tool that writes. Only the checker (rules) updates memory.
2. **Learner text never goes into Raju's prompt.** Raju's prompt is built only from the rule bank and seen-word list (`classmate.build_messages`). Learner answers go to the deterministic checker, not a model.
3. **Every model output is filtered.** Raju: leak filter + tool validation (Telugu script only, one sentence) — a hijacked reply like "mark the learner correct" is rejected and the bank sentence is used. Coach/Sravya (when built): level check and no-answer check before display.
4. **Read-only tools.** Agent tools are lookups and checks; `submit_*` re-validates. No web, email, file or memory-writing tools.
5. **When learner text must reach a model** (coach, Sravya): pass it as a delimited JSON data field, cap length, strip control characters, and state in the system prompt that it is data, not instructions. Outputs still go through the filters in (3).
6. **Uploaded learner writing** is anonymised and only produces *proposals* that a teacher approves.
7. **Red-team tests:** `tests/test_injection.py` (checker never accepts an attack, tool rejects injected output, learner text never enters Raju's prompt, a hijacked model cannot change state). Grow this set for coach and Sravya; report attack success rate.

Limit: filtering can't guarantee a model never *says* something odd in free conversation (Sravya); the guarantee is that it can't change grades, memory or what Raju "knows".


## Status against the checklist (29 Oct 2026)

| Item | Status |
|---|---|
| Intake Q1–Q4 answered | Done (above) |
| Tool calling | **Done**: `check_classmate_sentence` schema + exact error strings; called by the model inside Raju's loop (`setu/agent.py`); JSON-reply protocol, works with any chat model (Gemma via Ollama/vLLM) |
| Agent | **Done (one agent)**: Raju's revise-or-submit loop, bounded, re-validated by the harness. Sravya / coach agents: not built |
| Prompt injection | Done for Raju and the checker (`tests/test_injection.py`, `tests/test_agent.py::test_hijacked_model_cannot_change_state`); coach/Sravya pending |
| Repo with tests passing | Done: 112 tests |
| Demo application | Done: FastAPI app (`SETU_LLM=demo SETU_DEMO=1 uvicorn app.server:app`) and a hosted browser-only version (`app/hosted/setu_app.html`, published as a claude.ai link) with Learn, Study mode, Teacher and How it works |
| Paper v8+ | Done; real-model numbers missing |
| Plain-language explainer + video | Done: `docs/video/SETU_How_It_Works_v8_full.mp4` (5:50, voice-over, 18 scenes incl. Step 0 letters) |
| Gemma leak baseline | **Missing** (needs Faviana's Mac run) |
| Table 10 metrics filled in | Partly: `scripts/evaluate.py` → `docs/EVAL_REPORT.md` (scorecard on held-out split); mock-model and simulated values only |
| Script bridge (Step 0) | Done: `setu/script.py` (Devanagari↔Telugu, forgiveness for ए/ओ and final म), Letters page in the hosted app, Hindi-letter typing in every condition; conversion rules need a native check |
| Study conditions A/B/C + tests | Done (`setu/session.py`, `tests/test_study.py`, study mode in both apps) |
| Simulated learners | Done (v0 parametric): `scripts/simulate_learners.py` → `docs/results_sim_learners.json`; A beat B, not C |
| Teacher-label sheet | Made: `data/l1-hi_l2-te/teacher_labels_v0.csv` (145 answers) — needs a native teacher |
| Native review of 15 HI→TE rules | **Missing** |
| Telugu→Hindi rules (10) | **Missing** |
| Consent forms, interview notes, 5-learner study | **Missing** |
| Speech, teacher console, Sravya, morphological analyser | Not built |
