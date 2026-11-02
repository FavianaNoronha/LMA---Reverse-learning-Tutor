# Gemma run: Mac, start to finish

One run produces every real-model number we still lack: how often a plain prompt leaks, how the four ways of using the model compare (plain / prompt-only / resample / tool loop), model calls and time per turn, controllability with a real model, and simulated learners driven by Gemma.

## 0. Once only
1. Install Ollama from https://ollama.com/download, open it (llama icon in the menu bar).
2. In Terminal, in the repo folder:
   ```
   git pull
   source .venv/bin/activate
   pip install -r requirements.txt
   ollama pull gemma3:12b        # about 8 GB. On an 8 GB Mac use gemma3:4b instead
   ```

## 1. Run everything
```
bash scripts/run_gemma_all.sh                 # gemma3:12b, quick profile
bash scripts/run_gemma_all.sh gemma3:4b       # smaller model
bash scripts/run_gemma_all.sh gemma3:12b full # full profile, run overnight
```
It first checks that the server is up, the model is downloaded and that it answers in Telugu, then prints a time estimate. If something is wrong it says what to do and stops. Keep the Mac awake and plugged in (System Settings → Lock Screen, or run `caffeinate -i bash scripts/run_gemma_all.sh`).

| Profile | Plain-prompt leak test | Baselines | Controllability | Simulated learners | Time on a 12B model |
|---|---|---|---|---|---|
| quick | 3 per item | 1 rep | 3 learners | 2 per condition | roughly 30-90 min |
| full | 10 per item | 3 reps | 10 learners | 5 per condition | a few hours |

## 2. Send back
`docs/results_gemma/gemma_results.zip` (or paste `docs/results_gemma/SUMMARY.md`). The summary also records the Mac chip, memory and code commit, so we do not have to ask.

## 3. If it stops
- "NO SERVER": open the Ollama app.
- "MODEL is not downloaded": run the `ollama pull` line it prints.
- "ABORTED: first N model calls all failed": the server answered with errors; the message shows the first one. A run with errors is never reported as a result: any case with a model error is excluded and counted.
- Very slow or Mac freezes: use `gemma3:4b`.

## What the numbers mean
- **valid**: the sentence the learner would see has exactly the planned mistake, uses only words the learner has seen, and gives nothing away.
- **prompt_only / plain_no_reference**: nothing stops a bad sentence from being shown, so 1 − valid is how often it would be.
- **resample / tool**: the leak filter decides what is shown. The safety invariant (a shown sentence passes the filter again) is checked on real output and must hold on every case.
- Simulated-learner numbers follow from stated assumptions; they are not evidence about people.
