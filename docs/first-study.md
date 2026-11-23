# Run your first study

Use an empty project and try the steps in order. If you get stuck, copy the error into the [feedback template](trial-feedback.md). The person who invited you wants to learn where the guide needs work.

## 1. Try the starter

Use the [install commands and starter prompt](../README.md#start-here). Look for a result that names the two strategies and explains the measurement. **You can skip the prediction.** Here it just means “what do I expect to happen?”

## 2. Ask a question and change one thing

Try “Does exploring less lead to less missed reward in this simulation?” or rewrite it in your own words. Compare exploration weights of 200 and 50 (the tool uses hundredths). The higher weight gives exploration more influence. Both settings run on matched simulated cases. Keep the other settings the same.

For this comparison, record whether you expect the second setting to produce **lower**, **higher**, or **unchanged** reward loss before running. You can borrow the example expectation. “Unchanged” means you expect no change. If you're unsure, record that in your notes and treat the expectation as a guess. Recording it before the run helps you remember which ideas came from seeing the results.

Paste this into your agent, changing the question and expectation if you like.

> Use the installed Exoverse paired study for this question: “Does exploring less lead to less missed reward in this simulation?” Compare baseline exploration weight 200 with treatment weight 50 and keep everything else fixed. My pre-run expectation is lower reward loss at 50. Run both settings and use the paired CLI to save study.json and paper.md in a new folder called first-study. Give me the SHA-256 fingerprint the tool printed. Summarize what was measured and one limit of the result.

Look for `first-study/study.json`, `first-study/paper.md`, and a 64-character fingerprint. The draft reports what happened in the simulation. Save the fingerprint separately so you can use the original when checking the files.

## 3. Check the evidence in a new project

Copy the `first-study` folder into another empty project. Open a new agent session there. Replace `PASTE_ORIGINAL_FINGERPRINT` below with the fingerprint you saved.

> Use the installed Exoverse tool to verify first-study/study.json and first-study/paper.md against this original SHA-256 fingerprint: PASTE_ORIGINAL_FINGERPRINT. Tell me if verification passed. Then rerun the same comparison into a new folder called reproduced-study and compare the printed fingerprint and paper with the originals.

A successful check replays the recorded simulation and verifies the exact draft. Matching files show that the same setup gives the same result. A new dataset or model would be a separate experiment.

## If the agent gets stuck

- If your agent can't find the Exoverse tools, check that both install commands succeeded and start a fresh agent session in the project.
- If the tool won't start, run `python3 --version` in the same terminal and check that it's at least 3.9.
- If verification fails, check that you copied both files and the original fingerprint. Even a Markdown edit will change what the verifier sees. Keep any edited draft as a separate file.
- If the agent can't export the two files, use the release ZIP commands below and record what happened in your feedback.

## Run the same steps without an agent

Download and extract the [0.6.6 release ZIP](https://github.com/rudycelekli/exoverse-research/releases/tag/v0.6.6), then open a terminal in the extracted folder. Run:

```sh
plugins/exoverse/bin/exoverse-plugin starter run --out starter.json
plugins/exoverse/bin/exoverse-plugin paired run \
  --question 'Does exploring less lead to less missed reward in this simulation?' \
  --baseline 200 --treatment 50 --prediction lower --out first-study
```

Copy the printed fingerprint. To verify a copy of the folder in another project, run the following from the extracted package. Replace `/path/to/another-project/first-study` and `PASTE_ORIGINAL_FINGERPRINT` before running it.

```sh
plugins/exoverse/bin/exoverse-plugin paired verify \
  /path/to/another-project/first-study --sha256 PASTE_ORIGINAL_FINGERPRINT
```

To reproduce it, repeat the paired run command with a new output path such as `/path/to/another-project/reproduced-study` and compare the fingerprint with the original.

## Send feedback

Fill in the [feedback template](trial-feedback.md) and send it to your inviter. Describe the first place you hesitated, even if you got through it.
