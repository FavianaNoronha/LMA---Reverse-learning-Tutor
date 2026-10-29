"""Builds the learner-study pack: consent form (+ background questionnaire) and the facilitator's session script.
  python scripts/make_study_pack.py  -> docs/study/*.pdf"""
import glob, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "docs/study"; OUT.mkdir(parents=True, exist_ok=True)
SITE = "https://favianaNoronha.github.io/LMA---Reverse-learning-Tutor/"
CSS = """@page{size:A4;margin:16mm 16mm}body{font:10.4pt/1.5 'Noto Sans','Noto Sans Devanagari','Noto Sans Telugu',sans-serif;color:#1b2040}
h1{font:800 19pt/1.15 'Baloo 2','Noto Sans',sans-serif;margin:0 0 4px}h2{font:700 12.5pt/1.2 'Baloo 2','Noto Sans',sans-serif;margin:14px 0 4px;break-after:avoid}
p{margin:4px 0 7px}table{border-collapse:collapse;width:100%;margin:6px 0 10px;font-size:9.6pt}th,td{border:1px solid #cfd3e4;padding:5px 7px;text-align:left;vertical-align:top}
th{background:#eef0f8;font-size:8.6pt;text-transform:uppercase;letter-spacing:.04em}.box{display:inline-block;width:11px;height:11px;border:1.2px solid #1b2040;margin-right:6px;vertical-align:-1px}
.line{display:inline-block;border-bottom:1px solid #1b2040;min-width:200px;height:15px}.say{background:#ebe9fc;border-radius:6px;padding:7px 10px;margin:5px 0 8px;font-style:italic}
.note{background:#fbf2d6;border-radius:6px;padding:7px 10px;font-size:9.6pt;margin:6px 0}.pb{break-before:page}.muted{color:#5a6185}li{margin:2px 0}"""


def pdf(name, body, title):
    h = OUT / f"{name}.html"
    h.write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{CSS}</style></head><body>{body}</body></html>", encoding="utf-8")
    chrome = (glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome") or ["chromium"])[0]
    subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=3000",
                    f"--print-to-pdf={OUT / (name + '.pdf')}", h.as_uri()], check=True, capture_output=True, timeout=120)


consent = f"""
<h1>Participant information and consent</h1>
<p class='muted'>SETU: learning Telugu by teaching an AI classmate · LMA course project, IIIT Hyderabad · Team Token Guessers</p>
<div class='note'><b>For the team:</b> use this form only after the IIIT Hyderabad ethics process has approved the study, and fill in the reference number and the contact details below. Give the participant a copy to keep.</div>
<p><b>Ethics reference:</b> <span class='line'></span> &nbsp; <b>Contact person:</b> <span class='line'></span> &nbsp; <b>Email/phone:</b> <span class='line' style='min-width:150px'></span></p>
<h2>What is this study?</h2>
<p>We are testing a website that helps Hindi speakers learn basic Telugu. You learn a small grammar rule, then you correct the mistakes of an AI classmate called Raju. We want to know whether correcting Raju helps people remember Telugu better than studying examples or practising with a normal tutor. We are testing the website, not you.</p>
<h2>What will I do?</h2>
<table><tr><th>When</th><th>What</th><th>Time</th></tr>
<tr><td>Day 1</td><td>This form, a few questions about your languages, a short test, a letters tour, then practice in three ways</td><td>about 45 min</td></tr>
<tr><td>Day 2</td><td>Practice</td><td>about 20 min</td></tr>
<tr><td>Day 3</td><td>Practice, a short test, and a feedback form</td><td>about 30 min</td></tr>
<tr><td>One week later</td><td>A short test and a 5-minute conversation about your experience</td><td>about 20 min</td></tr></table>
<p>You type answers in Telugu or in Hindi letters. Tests have no right or wrong feedback. There is no audio or video recording.</p>
<h2>What data is kept, and how?</h2>
<ul><li>Your typed answers, test scores, time on the website and your feedback answers, stored under a code (for example P03), not your name.</li>
<li>Only the project team sees the data. Your name and this form are kept separately from the data and are not shared.</li>
<li>Results are reported only as group numbers or anonymous quotes, in a course paper and possibly a research publication.</li>
<li>The website runs in the browser on our laptop. It does not ask for your name, email or phone number.</li></ul>
<h2>Risks and benefits</h2>
<p>There are no known risks beyond the time it takes and the mild effort of a test. You may learn some Telugu. There is no payment<span class='line' style='min-width:120px'></span> (team: write any token of thanks here).</p>
<h2>Taking part is your choice</h2>
<p>You can stop at any time without giving a reason, and ask us to delete your data until the results are written up (date: <span class='line' style='min-width:110px'></span>). Stopping has no effect on your marks, job or relationship with anyone on the team.</p>
<h2>Consent</h2>
<p><span class='box'></span>I have read this sheet (or had it read to me) and could ask questions.</p>
<p><span class='box'></span>I am 18 or older, and I take part voluntarily.</p>
<p><span class='box'></span>I agree that my typed answers and feedback are stored under a code and used as described above.</p>
<p><span class='box'></span>I agree that short anonymous quotes from my feedback may be used. (optional)</p>
<p style='margin-top:14px'>Name: <span class='line'></span> &nbsp; Signature: <span class='line' style='min-width:150px'></span> &nbsp; Date: <span class='line' style='min-width:90px'></span></p>
<p>Researcher: <span class='line'></span> &nbsp; Signature: <span class='line' style='min-width:150px'></span> &nbsp; Participant code: <span class='line' style='min-width:60px'></span></p>

<h1 class='pb'>Background questions</h1>
<p class='muted'>Participant code: <span class='line' style='min-width:80px'></span> (no name on this page)</p>
<table>
<tr><td>1. Age group</td><td><span class='box'></span>18–24 <span class='box'></span>25–34 <span class='box'></span>35–44 <span class='box'></span>45+</td></tr>
<tr><td>2. Your first language (mother tongue)</td><td><span class='line'></span></td></tr>
<tr><td>3. How well do you speak Hindi?</td><td><span class='box'></span>Native <span class='box'></span>Very well <span class='box'></span>Well <span class='box'></span>Some</td></tr>
<tr><td>4. Can you read Hindi (Devanagari) letters?</td><td><span class='box'></span>Easily <span class='box'></span>Slowly <span class='box'></span>No</td></tr>
<tr><td>5. How much Telugu do you know now?</td><td><span class='box'></span>None <span class='box'></span>A few words <span class='box'></span>Simple sentences <span class='box'></span>More</td></tr>
<tr><td>6. Can you read Telugu letters?</td><td><span class='box'></span>No <span class='box'></span>A few <span class='box'></span>Slowly <span class='box'></span>Yes</td></tr>
<tr><td>7. How long have you lived in Telangana / Andhra Pradesh?</td><td><span class='box'></span>Not at all <span class='box'></span>&lt; 6 months <span class='box'></span>6 months–2 years <span class='box'></span>&gt; 2 years</td></tr>
<tr><td>8. Other languages you speak</td><td><span class='line'></span></td></tr>
<tr><td>9. Have you used a language app before (e.g. Duolingo)?</td><td><span class='box'></span>Yes, often <span class='box'></span>A little <span class='box'></span>No</td></tr>
<tr><td>10. Why do you want to learn Telugu? (optional)</td><td><span class='line' style='min-width:300px'></span></td></tr></table>
<p class='muted'>Exclusion: if the answer to 5 is “Simple sentences” or “More”, or 1 is under 18, thank the person and do not include them in the study.</p>
"""
pdf("SETU_Consent_Form", consent, "SETU consent form")

script = f"""
<h1>Learner study · facilitator's session script</h1>
<p class='muted'>For the team member running sessions with 4–5 adult Hindi speakers who do not know Telugu. Website: <b>{SITE}</b> → <b>Research team</b> page for the study tools.</p>
<h2>Before the first session</h2>
<ul><li>Ethics approval received; consent form filled in with the reference and contacts (two copies per person).</li>
<li><b>One browser profile per participant</b> on the study laptop (Chrome: profile icon → Add; name it P01, P02, …). The website keeps all progress in the browser, so each participant must always use their own profile on the same laptop, and nobody clears browser data during the study.</li>
<li>In each profile: open the website → Research team → Study → type the code (P01…) → <b>Assign conditions</b>. This splits the 15 rules into three groups of 5: A (teach Raju), B (study examples), C (normal tutor), rotated across participants.</li>
<li>Write down each person's condition order for practice (counterbalanced): P01 A→B→C, P02 B→C→A, P03 C→A→B, P04 A→C→B, P05 B→A→C.</li>
<li>Plan the dates: Day 1, Day 2, Day 3, and the delayed test exactly 7 days after Day 3 (±1 day).</li></ul>

<h2>Session plan</h2>
<table><tr><th>Day</th><th>Steps</th><th>Time</th></tr>
<tr><td>1</td><td>Welcome · consent · background questions · pre-test · letters tour · first practice block</td><td>45 min</td></tr>
<tr><td>2</td><td>Practice block</td><td>20 min</td></tr>
<tr><td>3</td><td>Practice block · post-test · feedback form</td><td>30 min</td></tr>
<tr><td>3 + 7 days</td><td>Delayed test · transfer test · short interview</td><td>20 min</td></tr></table>

<h2>Day 1</h2>
<p><b>1. Welcome (2 min).</b></p>
<div class='say'>“Thanks for coming. We're testing a website that teaches basic Telugu to Hindi speakers. We're testing the website, not you, so there are no wrong answers about it. It takes about 45 minutes today and three shorter sessions later.”</div>
<p><b>2. Consent and background (8 min).</b> Give the consent form; let them read; answer questions; both sign. They fill in the background questions with their code only. Check the exclusion line.</p>
<p><b>3. Pre-test (5 min).</b> Research team → Study → Tests → <b>Pre-test</b> → Start test, then hand over the laptop.</p>
<div class='say'>“This is a short test before you learn anything. You'll see a sentence in English and Hindi. Type it in Telugu, or in Hindi letters, as best you can. If you don't know, press ‘I don't know’. That's completely normal today.”</div>
<p><b>4. Letters tour (5 min).</b> Open <b>Letters</b> and let them go through the three steps.</p>
<div class='say'>“Telugu letters are cousins of Hindi letters, in the same order. Have a look; you don't need to learn them all. In the lessons you can always type in Hindi letters.”</div>
<p><b>5. Practice block (20 min), in their condition order.</b> About 6–7 minutes per condition:</p>
<table><tr><th>Condition</th><th>Where</th><th>What to say</th></tr>
<tr><td><b>A</b> teach Raju</td><td>Research team → Study → <b>Practise A in Learn</b> (opens Lessons, limited to A rules)</td><td>“Learn the rule, then check Raju's sentences. If he's wrong, fix his sentence.”</td></tr>
<tr><td><b>B</b> examples</td><td>Research team → Study → <b>Next example</b>, repeatedly</td><td>“Read each wrong sentence, the correction and the explanation. Take your time.”</td></tr>
<tr><td><b>C</b> normal tutor</td><td>Research team → Study → <b>Next sentence</b>, type, <b>Check</b></td><td>“Write the sentence in Telugu; the tutor corrects you.”</td></tr></table>
<p>Aim for the <b>same number of items in each condition</b> per session (about 6). Note the counts on the record sheet.</p>

<h2>Day 2</h2>
<p>Practice block as on Day 1, same order, about 6 items per condition (20 min).</p>

<h2>Day 3</h2>
<p>Practice block (20 min). Then <b>Post-test</b> (Research team → Study → Tests → Post-test). Then the <b>Feedback</b> page (System Usability Scale + 3 questions). Stay out of view while they answer.</p>

<h2>One week after Day 3</h2>
<p><b>1. Delayed test</b>, then <b>Transfer test</b> (new sentences). No practice before the tests.</p>
<div class='say'>“Same as the first test. Type the sentence in Telugu or Hindi letters. Don't worry if you've forgotten some.”</div>
<p><b>2. Interview (5 min).</b> Note answers in writing, no recording:</p>
<ol><li>Which way of practising did you like most, and why?</li><li>Did correcting Raju feel like teaching, or like a quiz?</li><li>What was confusing?</li><li>Did the Hindi letters help, or get in the way?</li><li>Would you use something like this to learn Telugu? What would make you use it?</li></ol>
<p><b>3. Export the data</b> (do this at the end of <i>every</i> session too):</p>
<ul><li>Research team → Study → <b>Copy results as CSV</b> → paste into the team sheet <i>study_results</i> (one tab per participant).</li>
<li>Research team → Demo controls → <b>Copy all feedback as CSV</b> → paste into <i>feedback</i>.</li>
<li>Do <b>not</b> press Reset until all data is exported and checked.</li></ul>

<h2>Rules for the facilitator</h2>
<ul><li>Never tell a participant whether an answer is right during practice or tests; the website does that during practice, and nobody does it during tests.</li>
<li>Give the same help in every condition. The reading aids (Hindi letters, listen button, Hindi-letter typing) stay on for all three.</li>
<li>Don't explain the rules yourself. If asked, say: “Use what's on the screen; you're doing fine.”</li>
<li>Test answers are marked later by a Telugu teacher from <b>outside</b> the team who does not know which condition each rule was in.</li>
<li>If something breaks, write down what happened and the time, and continue in the same browser profile.</li></ul>

<h2>Record sheet (one per participant)</h2>
<table><tr><th>Code</th><th>Order</th><th>Day 1 date · items A/B/C</th><th>Day 2 date · items A/B/C</th><th>Day 3 date · items A/B/C</th><th>Delayed test date</th><th>Data exported?</th></tr>
<tr><td style='height:26px'></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td style='height:26px'></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
<tr><td style='height:26px'></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td style='height:26px'></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
<tr><td style='height:26px'></td><td></td><td></td><td></td><td></td><td></td><td></td></tr></table>
<p class='muted'>The paper (Section 8.3) describes this design: within-learner, three conditions on different rules by Latin square, matched exposure and feedback, delayed and transfer tests marked blind. With 4–5 learners, results are reported as effect sizes with confidence intervals, without significance claims.</p>
"""
pdf("SETU_Session_Script", script, "SETU session script")
for f in OUT.glob("*.html"):
    f.unlink()
print("ok", sorted(p.name for p in OUT.iterdir()))
