---
name: exoverse-research-team
description: Coordinate research planning, execution, independent replay, scoped memory and review using the host harness and Exoverse evidence.
---

# Research team and memory

Create a short work record with a question, one owner per task, a budget,
an acceptance test and an evidence path. Assign three roles:

- The coordinator freezes the question, comparison and evidence criteria.
- The experiment runner executes both arms and returns exact receipts, errors
  and the independently retained digest.
- The reviewer receives only the evidence files and digest, verifies them and
  reports disagreement. Keep its conclusions separate from the runner's.

Use the host's own delegation capability when it is available and authorized.
Otherwise work through the roles separately and label a rerun as self-review.
A future human or agent should be able to pick up the work through the local
protocol and receipt rather than relying on the conversation or an opaque
memory store. Save a short source-linked research record in the workspace
only when useful to the user's task.

For the completion-monitor study, preserve the export and its original digest.
Use `exoverse-plugin review STUDY --sha256 SEAL --out REVIEW` to replay the
study and draft. When the user approved local adapters and provided their
installed executable paths, add `--ifixai-python` for a passive iFixAI policy
audit. Add `--ruflo` to record the verified audit digests in a local Ruflo
task. Distinguish replay, external policy audit and Ruflo task tracking in
the result. A completed task refers to a completed automated audit.

If a qualified RuVector or Claude-mem connection is configured, index only
approved evidence and retain exact source references. Use Firecrawl for
permitted source discovery when authorized. The local experiment and
verifier are available without external integrations.
