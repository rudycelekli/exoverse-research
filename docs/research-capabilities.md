# Research capabilities and evidence

| Private capability | Public integration point | Acceptance evidence |
| --- | --- | --- |
| Environment adapters and branchable universes | Use the same observation, action, reward, termination and capability model. Export pinned worlds and checkpoint lineage. | Restore a checkpoint in an independent process and reproduce the next transition. Refuse branching on adapters without snapshots. |
| Spec-writing skills | Give authors a question-to-spec flow that records the changed variable, seed list, budget, success criteria and baseline before any run. | Fresh researchers use their own workflow, confirm allowed actions and validate controls before execution. |
| Rubrics and LLM judges | Run explicit trajectory checks first. Add versioned qualitative rubrics as separate evaluators with examples and abstention. | On blinded holdouts, measure agreement with humans and report unsupported cases, false positives and false negatives. |
| Research analytics | Compute paired deltas, coverage, uncertainty, failures, time and cost from immutable traces. | Recompute all reported statistics from a clean workspace and keep launch failures out of reward totals. |
| Novelty and scientific value | Attach each claim to source passages, nearby prior work and an evidence artifact. Preserve disagreements and expert judgments. | Check citation support independently, surface closest prior art and label novelty judgments provisional until reviewed. |

Researcher value needs an observed test: an unaided user authors a new environment, verifies a meaningful result on a second machine, and explains the alternatives the evidence rules out. Pair that with time to first verified result, repeatability, evaluator accuracy and human effort. The public package should retain local authoring, runtime and verification. Private infrastructure can expand throughput, protected data access and governance while using the same evidence contract.
