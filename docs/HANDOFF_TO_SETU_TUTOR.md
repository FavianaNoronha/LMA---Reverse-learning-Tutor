# Hand-off to the `setu-tutor` repo (Madhav)

Source: this repo (`FavianaNoronha/LMA---Reverse-learning-Tutor`), commit after `c11a63a` (your vendored snapshot is frozen at `c11a63a`, which predates everything below). Nothing here edits your repo; it lists what to import and how.

## 1. What changed since `c11a63a`
| Item | Where in this repo | What to do on your side |
|---|---|---|
| 145 blind labels by a bilingual team member | `data/l1-hi_l2-te/teacher_labels_v0.csv` (columns: `teacher_verdict`, `teacher_verdict_raw`, `teacher_note`, `checker_verdict_at_return`) | Run all 145 answers through `checker-1` and fill M-16 (κ target 0.6). Your checker has a *partial* verdict; her labels say the 29 answers with extra `కదా` are **wrong**, not partial. |
| Tag-particle rule (checker v0.2) | `setu/checker.py` (`TAG_PARTICLES`) | Add to `checker-1` as a wrong pattern: accepted form + ` కదా` = wrong, reason "tag question". Fitted to those 29 rows, so test it on fresh rows. |
| Item level A1/A2/B1, frequency, review notes | `rules.json` items: `level`, `frequency`, `review_notes` | Import as new rule versions via `content/hi-te` and `content/te-hi` YAML (do not edit the vendored snapshot). |
| Review status | `rules.json` `status`/`reviewer`/`reviewed_at` | 24 of 25 rules `native_checked` by one team member; HI-TE-012 not. This is a team-member check, not the two independent raters your teacher console expects. |
| Returned sheets (raw) | `docs/reviewer_pack/returned/` | Sheet 1 lost its Telugu text (ASCII save): re-export as CSV UTF-8 before importing alternates. |
| Findings and open questions | `docs/REVIEW_RETURN_2026-11.md` | Questions for the reviewer: missing final vowel sign, five probable label slips, B2 level, `मेरे को` policy. |

## 2. Candidate new rules from sheet 5 (each needs 2 items, a regex, native check)
HI→TE: `నేను బాగుంది` → `బాగున్నాను`; `నువ్వు వస్తున్నాను` → `వస్తున్నావు`. TE→HI: drop को in `घर को जा रहा हूँ`; verb agreement with मैं/तुम (`जाता है`, `जा रहा है`); `मेरे को` vs `मुझे` with ने. `నేనేం చేస్తున్నాను` is a spoken-form recognition item, not a mistake.

## 3. Things in this repo not in yours (check the ones you want)
Script bridge with reading aid (`setu/script.py`); the revise-or-submit agent loop (`setu/agent.py`); half-life simulated learners with a 5-assumption sensitivity grid (`scripts/simulate_learners.py`); study pack and consent form (`docs/study/`); reviewer pack; browser-only hosted site; paper v9 (`docs/paper/`) and video v8.

## 4. Conflicts to settle as a team
1. **Which repo is the submission?** Your ADR-0001 retires the hosted JS app; our README, video and Pages link point at it.
2. **Self-hosted models only (ADR-0003) vs the Gemini run** in `reports/generation_baselines_run1_rate_limited.json`. Report it as a development run only.
3. **No local Gemma numbers exist yet** (ours or yours). `scripts/plain_prompt_leak_test.py` and `scripts/simulate_learners.py` run against any OpenAI-compatible URL.
4. **Credit:** the reviewer asked to be named how? Initials are still "pending" in every `reviewer` field.
