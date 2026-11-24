# Research capabilities and evidence

| Private capability | Public integration point | Acceptance evidence |
| --- | --- | --- |
| Environment adapters and branchable universes | Use the same observation, action, reward, termination and capability model. Export pinned worlds and checkpoint lineage. | Restore a checkpoint in an independent process and reproduce the next transition. Refuse branching on adapters without snapshots. |
| Spec-writing skills | Give authors a question-to-spec flow that records the changed variable, seed list, budget, success criteria and baseline before any run. | Fresh researchers use their own workflow, confirm allowed actions and validate controls before execution. |
| Rubrics and LLM judges | Run explicit trajectory checks first. Add versioned qualitative rubrics as separate evaluators with examples and abstention. | On blinded holdouts, measure agreement with humans and report unsupported cases, false positives and false negatives. |
| Research analytics | Compute paired deltas, coverage, uncertainty, failures, time and cost from immutable traces. | Recompute all reported statistics from a clean workspace and keep launch failures out of reward totals. |
| Novelty and scientific value | Attach each claim to source passages, nearby prior work and an evidence artifact. Preserve disagreements and expert judgments. | Check citation support independently, surface closest prior art and label novelty judgments provisional until reviewed. |

Researcher value needs an observed test: an unaided user authors a new environment, verifies a meaningful result on a second machine, and explains the alternatives the evidence rules out. Pair that with time to first verified result, repeatability, evaluator accuracy and human effort. The public package should retain local authoring, runtime and verification. Private infrastructure can expand throughput, protected data access and governance while using the same evidence contract.

## Adapter launch plan

A fresh install should take a researcher from their own question to a verified
result. Ship a complete offline study with local scoring and verification.
Expose additional adapters in the same study flow, with a setup action and
clear availability status. Make CLI commands and browser controls use the same
backend and evidence format.

| Capability | Launch placement | Next proof |
| --- | --- | --- |
| Local workflows, deterministic policies, rubrics and evidence | Default offline path | Author a custom workflow, compare two policies and verify the export on another machine. |
| Claude Code and Codex | One-click live execution after provider setup | Run the same frozen workflow in separate containers through a bounded gateway. Verify both results offline. |
| Portkey and additional model routes | Credentialed gateway | Prove route isolation, request budgets, usage receipts and honest reporting of failures. |
| Ruflo and iFixAI | Optional orchestration and independent review | Qualify setup from a clean browser profile, restart persistence and offline continuation. |
| Harbor and Terminal-Bench | Optional benchmark packs | Pin a benign benchmark task and image, run it from a fresh install and verify the score and trace. |
| Penguin Harness | Optional harness-optimization candidate | Compare immutable baseline and candidate harness snapshots on the same model and held-out cases. Keep promotion an explicit review decision. |
| Firecrawl and literature tools | Optional source collection | Record source URLs, retrieval dates and supporting passages so the evidence can be reviewed against the original sources. |
| RuVector and memory adapters | Optional local research recall | Prove project scoping, provenance and deletion. Keep retrieved research distinct from measured results. |
| TestSprite and browser replay tools | Optional product qualification | Reproduce a first-study journey in a clean profile and bind its receipt to the tested release. |

Each adapter needs a pinned version, supported platforms, credential and network
requirements, a health probe, and a clean-install proof. The study records the
adapter version and configuration fingerprint with the results. Setup failures
produce diagnostics, while completed evaluations produce scores. Evidence
verification uses the exported artifacts and stays available offline.

Public releases should include the local research loop and the adapter
interface. Hosted execution, shared budget management, private registries and
team workflows can extend it through the same interface.

Penguin Harness documents a fixed-model evolution loop with candidate snapshots
and benchmark-based scoring. Exoverse can adopt the experiment pattern first.
Packaging its runtime requires a scoped compatibility test, license and notice
review, and evidence that its execution model fits Exoverse's isolation boundary.
[Penguin Harness self-evolution](https://github.com/Prism-Shadow/penguin-harness#self-evolution)
