"""Builds the native-reviewer work pack: a PDF workbook and the CSV sheets to fill in.
  python scripts/make_reviewer_pack.py   -> docs/reviewer_pack/
Re-run whenever the rule banks change. PDF needs Chromium (Playwright's is used if present)."""
import csv, glob, html, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from setu.bank import load_rules
from setu.script import telugu_to_deva, DIFFERENCES

OUT = ROOT / "docs/reviewer_pack"; OUT.mkdir(parents=True, exist_ok=True)
HT, TH = load_rules("l1-hi_l2-te"), load_rules("l1-te_l2-hi")
QCOLS = ["Q1_realistic (often/sometimes/rarely/never)", "Q2_exactly_one_mistake (yes/no + which)",
         "Q3_correct_is_natural (yes/formal/no)", "Q4_better_or_other_correct_forms (separate with |)",
         "Q5_explanation_right (yes/partly/no + fix)", "Q6_level (A1/A2/B1)", "notes"]


def sheet(rules, path, l1, l2):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["rule_id", "rule_name", "explanation_shown_to_learner", "item_id", "english", f"{l1}_meaning",
                    f"raju_sentence_with_mistake ({l2})", f"correct_sentence ({l2})", "other_accepted"] + QCOLS)
        for r in rules:
            for i in r.items:
                gloss = i.hindi if l1 == "Hindi" else i.telugu
                w.writerow([r.rule_id, r.name, r.l1_habit, i.item_id, i.english, gloss, i.planted_error, i.accepted[0],
                            " | ".join(i.accepted[1:])] + [""] * len(QCOLS))


sheet(HT, OUT / "1_review_hindi_to_telugu_rules.csv", "Hindi", "Telugu")
sheet(TH, OUT / "2_review_telugu_to_hindi_rules.csv", "Telugu", "Hindi")
# script conversion check
words = []
for r in HT:
    for i in r.items:
        words += [i.accepted[0]]
script_rows = [("ఇది పుస్తకం", "इदि पुस्तकं"), ("ఎవరు", "ऎवरु"), ("ఏమిటి", "एमिटि"), ("ఒకటి", "ऒकटि"), ("పళ్ళు", "पळ्ळु"),
               ("మేము వెళ్తున్నాం", "मेमु वॆळ्तुन्नां")] + [(w, telugu_to_deva(w)) for w in words[:8]]
with open(OUT / "4_check_script_conversion.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["telugu", "shown_in_hindi_letters", "Q_would_a_Hindi_reader_say_it_right (yes/no)", "better_hindi_letters", "notes"])
    for a, b in script_rows:
        w.writerow([a, b, "", "", ""])
with open(OUT / "5_new_rules_and_spoken_forms.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["direction (HI->TE or TE->HI)", "mistake_you_have_heard", "correct_form", "spoken_form_if_different",
                                   "why_learners_make_it", "how_often (often/sometimes)", "where_you_heard_it (class, office, auto, ...)"])
    for _ in range(10):
        w.writerow([""] * 7)
# blind label sheet: copy without the checker's verdict
src = list(csv.DictReader(open(ROOT / "data/l1-hi_l2-te/teacher_labels_v0.csv", encoding="utf-8")))
with open(OUT / "3_mark_learner_answers_BLIND.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["id", "item_id", "english", "learner_answer", "your_verdict (correct/wrong/unsure)", "why (optional)"])
    for r in sorted(src, key=lambda x: x["answer"]):        # shuffled order so variants are not grouped
        w.writerow([r["id"], r["item_id"], r["english"], r["answer"], "", ""])

E = html.escape
def rule_tables(rules, l1):
    out = []
    for r in rules:
        rows = "".join(f"<tr><td>{E(i.english)}<div class='g'>{E(i.hindi if l1 == 'Hindi' else i.telugu)}</div></td>"
                       f"<td class='x'>{E(i.planted_error)}</td><td class='ok'>{E(' / '.join(i.accepted))}</td>"
                       f"<td class='box'>☐ often ☐ sometimes<br>☐ rarely ☐ never</td><td class='box'>☐ natural<br>☐ formal ☐ wrong</td></tr>" for i in r.items)
        out.append(f"<div class='rule'><h4>{E(r.rule_id)} · {E(r.name)}</h4><p class='hab'>Explanation shown to learners: {E(r.l1_habit)}</p>"
                   f"<table><tr><th>Meaning</th><th>Raju's sentence (planted mistake)</th><th>Correct sentence(s)</th><th>Q1 Realistic?</th><th>Q3 Correct is…</th></tr>{rows}</table></div>")
    return "".join(out)

REFS = [
    ("Krishnamurti, Bh. and Gwynn, J. P. L. (1985). <i>A Grammar of Modern Telugu</i>. Oxford University Press.", "Main grammar for the Telugu side, written for non-native adults. Check the explanation (Q5) of each Hindi→Telugu rule."),
    ("Telangana SCERT Telugu textbooks: <i>Tenepalukulu</i> (classes I–V, simple Telugu for children whose home language is not Telugu) and <i>Vennela</i> (VI–X).", "Standard school spelling and simple everyday words. Good for Q3 (is the correct sentence standard?) and Q6 (level)."),
    ("Brown, C. P. <i>A Telugu–English Dictionary</i> (2nd ed. 1903; public domain, searchable online at the Digital South Asia Library, University of Chicago).", "Spelling and meaning of single words."),
    ("Andhra Bharati online Telugu dictionaries (andhrabharati.com).", "Quick spelling check of modern words."),
    ("NCERT Hindi textbooks (classes VI–X) and their grammar (व्याकरण) chapters.", "Standard Hindi for the Telugu→Hindi rules: gender, ने, agreement, oblique forms (Q3, Q5)."),
    ("Kendriya Hindi Nideshalaya (Central Hindi Directorate). <i>Devanagari Lipi tatha Hindi Vartani ka Manakikaran</i> (standard Hindi spelling).", "Rule TE-HI-008: when में, को, से are written apart (after nouns) and joined (after pronouns: मुझको, उसने)."),
    ("McGregor, R. S. <i>Outline of Hindi Grammar</i> (Oxford) or Snell, R. <i>Complete Hindi</i> (Teach Yourself).", "Clear English explanations of Hindi grammar for Q5."),
    ("CIIL (2003). <i>Tests of Language Proficiency: Telugu</i>, ed. Pon Subbaiah and M. Balakumar (Bhasha Sanchika repository).", "Optional: how a government test grades Telugu proficiency, for Q6 (level)."),
]

page = f"""<!doctype html><html><head><meta charset='utf-8'><title>SETU native reviewer workbook</title><style>
@page {{ size:A4; margin:16mm 15mm; }}
body {{ font: 10.2pt/1.45 'Noto Sans','Noto Sans Telugu','Noto Sans Devanagari',sans-serif; color:#1b2040; }}
h1 {{ font: 800 22pt/1.1 'Baloo 2','Noto Sans',sans-serif; margin:0 0 4px; }} h1 span {{ color:#c97412; }}
h2 {{ font: 700 14pt/1.2 'Baloo 2','Noto Sans',sans-serif; margin:18px 0 6px; border-bottom:2px solid #dcdfec; padding-bottom:3px; break-after:avoid; }}
h3 {{ font-size:11pt; margin:12px 0 4px; break-after:avoid; }} h4 {{ font-size:10.5pt; margin:10px 0 2px; }}
.lead {{ font-size:11pt; color:#4a5175; }}
table {{ border-collapse:collapse; width:100%; margin:4px 0 8px; font-size:9.2pt; }}
th, td {{ border:1px solid #cfd3e4; padding:4px 6px; text-align:left; vertical-align:top; }}
th {{ background:#eef0f8; font-size:8.4pt; text-transform:uppercase; letter-spacing:.04em; }}
td.x {{ color:#bd3a33; font-size:10.5pt; }} td.ok {{ color:#23824a; font-size:10.5pt; }} td.box {{ font-size:8.6pt; white-space:nowrap; }}
.g {{ color:#5a6185; font-size:9pt; }} .hab {{ margin:0 0 3px; color:#4a5175; font-size:9pt; }}
.rule {{ break-inside:avoid; }}
.task {{ border:1px solid #dcdfec; border-left:5px solid #4a40c4; border-radius:6px; padding:8px 11px; margin:7px 0; break-inside:avoid; }}
.task b.t {{ font-size:11pt; }} .time {{ float:right; color:#5a6185; font-size:9pt; }}
.note {{ background:#fbf1d3; border-radius:6px; padding:7px 10px; font-size:9.4pt; margin:6px 0; }}
.ex {{ background:#e0f3e7; border-radius:6px; padding:7px 10px; font-size:9.4pt; }}
ol li, ul li {{ margin:2px 0; }}
.pb {{ break-before:page; }}
</style></head><body>
<h1>SETU · native reviewer <span>workbook</span></h1>
<p class='lead'>For a reviewer who speaks both Telugu and Hindi. You make the tutor's language right; your answers decide which sentences learners will see. Thank you.</p>
<p><b>What SETU is.</b> A tutor where Hindi speakers learn Telugu (and later Telugu speakers learn Hindi) by correcting an AI classmate, Raju. Raju makes the mistakes a Hindi speaker typically makes in Telugu; the learner fixes them. Every mistake and every correct sentence comes from a small rule book. Today the rule book was written by us with an AI and has <b>not</b> been checked by a native speaker. That is your job.</p>
<div class='note'><b>Total time:</b> about 4–5 hours, in any order, over a few sittings. Tasks 1 and 3 matter most. Please don't use an AI tool to answer; we need your own judgement. If you are unsure, write “unsure” and why: that is a useful answer.</div>

<h2>Your tasks</h2>
<div class='task'><span class='time'>≈ 2 h · most important</span><b class='t'>Task 1 · Check the 15 Hindi→Telugu rules</b> (30 sentences)<br>
File: <b>1_review_hindi_to_telugu_rules.csv</b>. For every row answer Q1–Q6 (guide below). Most important: is Raju's sentence a mistake Hindi speakers really make, and is the “correct” Telugu natural and standard?</div>
<div class='task'><span class='time'>≈ 1 h · most important</span><b class='t'>Task 3 · Mark 145 learner answers</b><br>
File: <b>3_mark_learner_answers_BLIND.csv</b>. For each answer write <b>correct</b>, <b>wrong</b> or <b>unsure</b> for the English meaning given. Judge as a teacher would: would you accept it in class? Spelling slips count as wrong; a different but correct way of saying it counts as correct. The tutor's own verdicts are hidden on purpose; we compare them with yours afterwards.</div>
<div class='task'><span class='time'>≈ 1.5 h</span><b class='t'>Task 2 · Check the 10 Telugu→Hindi draft rules</b> (20 sentences)<br>
File: <b>2_review_telugu_to_hindi_rules.csv</b>. Same questions, the other way round: mistakes Telugu speakers make in Hindi (gender, ने, oblique मेरे, joined postpositions, missing है, relative clauses). Is each a real Telugu-speaker mistake? Is the Hindi standard? Please also suggest rules we missed in Task 5.</div>
<div class='task'><span class='time'>≈ 20 min</span><b class='t'>Task 4 · Check the Hindi-letter reading aid</b><br>
File: <b>4_check_script_conversion.csv</b>. The tutor shows every Telugu sentence in Hindi letters (Devanagari) so Hindi speakers can read it. For each row: would a Hindi reader say it correctly from these letters? If not, write a better spelling. Watch short ఎ/ఒ (shown as ऎ/ऒ), ళ (shown as ळ) and words ending in ం.</div>
<div class='task'><span class='time'>≈ 1 h · optional</span><b class='t'>Task 5 · Add spoken forms and missing rules</b><br>
File: <b>5_new_rules_and_spoken_forms.csv</b>. Hyderabad Telugu as spoken often differs from textbook Telugu (e.g. వస్తున్నా beside వస్తున్నాను). Write spoken forms learners will hear, and mistakes you have heard Hindi speakers make in Telugu (or Telugu speakers in Hindi) that are not in our list.</div>

<h2>How to answer Q1–Q6</h2>
<table><tr><th>Question</th><th>What to write</th></tr>
<tr><td><b>Q1</b> Is Raju's mistake realistic?</td><td><b>often</b> / <b>sometimes</b> / <b>rarely</b> / <b>never</b>. Would a Hindi speaker learning Telugu really say this? “never” means we should drop or change the rule.</td></tr>
<tr><td><b>Q2</b> Exactly one mistake?</td><td><b>yes</b>, or <b>no</b> and what the other mistake is. Raju's sentence must be correct except for the one planted mistake.</td></tr>
<tr><td><b>Q3</b> Is the correct sentence natural?</td><td><b>yes</b> / <b>formal</b> (correct but bookish) / <b>no</b>, and write the better sentence in Q4.</td></tr>
<tr><td><b>Q4</b> Other correct forms</td><td>Every other way a learner could correctly say it, including spoken forms. Separate with <b>|</b>. The tutor accepts only what is listed, so this column matters.</td></tr>
<tr><td><b>Q5</b> Is the explanation right?</td><td><b>yes</b> / <b>partly</b> / <b>no</b>, with a corrected explanation. This text is shown to learners as the hint.</td></tr>
<tr><td><b>Q6</b> Level</td><td><b>A1</b> (first weeks: survival phrases), <b>A2</b> (simple everyday sentences), <b>B1</b> (connected speech). Rough is fine; it orders the lessons.</td></tr></table>
<div class='ex'><b>Example of a filled row</b> · HI-TE-002-a · “This is a book.” · Raju: ఇది పుస్తకం ఉంది · correct: ఇది పుస్తకం →
Q1 <i>often</i> · Q2 <i>yes</i> · Q3 <i>yes</i> · Q4 <i>ఇది ఒక పుస్తకం</i> · Q5 <i>yes</i> · Q6 <i>A1</i> · notes <i>Hindi speakers add ఉంది because of है.</i></div>

<h2>Books and sources to check against</h2>
<p>Your own judgement comes first. Use these when you are not sure, and write in <i>notes</i> which one you used. One grammar and one dictionary are enough.</p>
<table><tr><th>Source</th><th>Use it for</th></tr>{''.join(f'<tr><td>{a}</td><td>{b}</td></tr>' for a, b in REFS)}</table>

<h2>Returning your work</h2>
<ol><li>Open the CSV files in Google Sheets or Excel (they open directly; keep the column order and don't rename columns).</li>
<li>Fill the empty columns. Leave a cell empty if you skip it.</li>
<li>Send the files back (or share the Google Sheet). We update the rule book, mark each rule <i>native_checked</i> with your initials and the date, and re-run the tests.</li>
<li>With your permission we will thank you by name in the paper's acknowledgements. We do not collect any personal data about you.</li></ol>

<h2 class='pb'>Task 1 on paper · Hindi→Telugu rules</h2>
<p>The same 30 sentences as in the CSV, if you prefer to tick on paper. Q2, Q4, Q5 and Q6 go in the CSV.</p>
{rule_tables(HT, 'Hindi')}
<h2 class='pb'>Task 2 on paper · Telugu→Hindi draft rules</h2>
{rule_tables(TH, 'Telugu')}
<h2>Reference: what is new in Telugu letters for a Hindi reader</h2>
<table><tr><th>Telugu</th><th>Hindi letters</th><th>Note</th></tr>{''.join(f"<tr><td style='font-size:12pt'>{E(d['telugu'])}</td><td style='font-size:12pt'>{E(d['deva'])}</td><td>{E(d['note'])}</td></tr>" for d in DIFFERENCES)}</table>
</body></html>"""
(OUT / "workbook.html").write_text(page, encoding="utf-8")
chrome = (glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome") or ["chromium"])[0]
subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=4000",
                f"--print-to-pdf={OUT / 'SETU_Native_Reviewer_Workbook.pdf'}", (OUT / "workbook.html").as_uri()], check=True, capture_output=True, timeout=120)
print("ok", sorted(p.name for p in OUT.iterdir()))
