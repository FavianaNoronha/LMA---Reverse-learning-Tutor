# Native review: what came back (2 Nov 2026)

Reviewer: one bilingual team member (not independent; initials still to be added). Files are in `docs/reviewer_pack/returned/`.
Merged with `scripts/ingest_returned_sheets.py`.

## Sheet 3 – 145 blind labels vs the checker
| | Agreement | κ | Unsure rate |
|---|---|---|---|
| Checker when labels returned (v0.1) | 92/145 = 63% | 0.32 | 20% (29 rows) |
| After adding the tag-particle rule (v0.2) | 121/145 = 83% | 0.599 | 0% |

**The v0.2 number is not independent evidence.** The tag-particle rule was written after seeing these 29 rows, so the second row is fitted to them. It needs fresh rows (other particles, other items) before it counts. The honest result is the first row.

What the disagreements were:
1. **29 rows, "extra word added" (కదా):** checker said *unsure*, reviewer said *wrong* every time (it turns the sentence into a tag question). Fixed: `TAG_PARTICLES` in `setu/checker.py`. Other extra words still go to the teacher.
2. **18 of 29 "one letter dropped" rows marked correct, 11 wrong, with no clean rule.** The same pattern is split: `…ఉన్నాన` wrong in HI-TE-004-a but correct in HI-TE-004-b; `…తింటున్నాన` correct but `…వెళ్తున్నాన` wrong. Checker left unchanged (still says wrong). **Open question for the reviewer:** is a missing final vowel sign a real spoken spelling, or a typo? (Her own sheet 5 writes spoken forms as `…వెళ్తున్నా` / `…వస్తున్నావ్`, which differ from these.)
3. **Five rows that look like slips, to re-confirm with her:**
   - TL-052 `మనం వెళ్తున్నాం` for "we, not you" marked correct. That form includes the listener, which is the planted error of HI-TE-006.
   - TL-102 `నాకు అన్నం తిన్నాను` marked correct. That is the planted error of HI-TE-011, and TL-097 (same mistake, other item) was marked wrong.
   - TL-137 `నేను ఇంట్లో వెళ్తున్నాను` marked correct. Her own sheet 5 lists this as a common mistake.
   - TL-026 `నీకు ఒక పెన్ను ఉంది` marked wrong; it is the accepted form, and TL-021 (same pattern) was marked correct.
   - TL-037 `నేను గది లో ఉన్నాను` marked correct. Spaced `లో` is the planted error of HI-TE-004. This may be a real orthography question rather than a slip.
4. **TL-032 `నేను ఇల్లు లో ఉన్నాను`:** "partially correct", which is not one of the three allowed verdicts. Scored as *unsure*.

## Sheets 1 and 2 – rule review
- **TE→HI (sheet 2):** all 10 rules: realistic, exactly one mistake, natural, explanation right. Levels A1/A2/B1. Marked `native_checked`.
- **HI→TE (sheet 1):** 14 of 15 rules fully "yes". **HI-TE-012 (object marker -ను on people): explanation "partly" right, and no fix was written.** It stays unreviewed until we have the fix.
- **Sheet 1 lost all its Telugu text** (saved as plain ASCII, so every Telugu letter became `?`). Ratings and levels are usable (joined on item_id); her "other correct forms" for those 15 rules are lost. **Needs a re-export as "CSV UTF-8".**
- Levels: she used **B2** for HI-TE-011-a, outside the A1/A2/B1 scale offered. Kept as given.
- HI-TE-008 (third-person verb agreement, our "positive-transfer control") was rated *rarely/sometimes*, yet sheet 5 lists `ఆమె వస్తాడు` as an *often* classroom mistake. Both can't be right; ask.
- Her "other correct forms" (sheet 2) are stored as notes only, **not** accepted by the checker. Several change the meaning or register (`चाय स्वादिष्ट है` = "tasty", `रवि अपने घर पर है`, `आपकी कार…` for तुम).

## Sheet 4 – script conversion: 12 of 14 pass
- `ఎవరు → ऎवरु`: she prefers `एवरु`. `మేము వెళ్తున్నాం → मेमु वॆळ्तुन्नां`: she prefers `मेमु वेळ्तुन्नाम्`.
- Her fixes drop the short-vowel marks (ऎ, ॆ), but she accepted them elsewhere (`ऒकटि`, `पॆन्नु`). Two rows are too few to change the converter; **decision needed: keep short-vowel marks or not.**

## Sheet 5 – new rules and spoken forms (10 rows)
Candidate new rules (none added yet, each needs 2 items, a regex and a native check):
- HI→TE: `నేను బాగుంది` → `బాగున్నాను` (people vs things); `నువ్వు వస్తున్నాను` → `వస్తున్నావు` (person ending).
- TE→HI: `मैं घर को जा रहा हूँ` (drop को); `मैं स्कूल जाता है` / `तुम कहाँ जा रहा है` (verb agreement with मैं/तुम); `वह मेरे को दिया` (मुझे and ने).
- `నేనేం చేస్తున్నాను` is a spoken-form recognition item, not a mistake.
- `मेरे को पानी चाहिए` is a regional (Hyderabad) spoken Hindi form: mistake and correct form are identical in her row. We need a policy: accept as a spoken variety, or teach standard `मुझे`.
