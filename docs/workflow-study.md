# Turn a workflow into a study

Describe a workflow as states and allowed actions. Each action moves to one
declared state. Give two named policies a choice for every nonterminal state.
Both policies start from the same state and receive independent episode state.
The interpreter handles only these declared transitions.

Save this example as `workflow.json`. Change the states, action choices, and
success criterion to capture a workflow of your own.

```json
{
  "initial": "draft",
  "states": {
    "draft": {"check": "checked", "submit": "rejected"},
    "checked": {"submit": "accepted"},
    "accepted": {},
    "rejected": {}
  },
  "criteria": {"goal": "accepted", "within_steps": 2},
  "max_steps": 4,
  "policies": {
    "check-first": {"draft": "check", "checked": "submit"},
    "submit-first": {"draft": "submit", "checked": "submit"}
  }
}
```

```sh
plugins/exoverse/bin/exoverse-plugin workflow run workflow.json --out evidence.json
plugins/exoverse/bin/exoverse-plugin workflow verify evidence.json --sha256 ORIGINAL_FINGERPRINT
```

Copy the printed fingerprint separately. Verification recomputes both
traces, termination, reward, and whether the goal was reached by the
deadline. A timeout is recorded as truncation. This is a state-isolated
simulation with scripted policies. Connecting a real application, running
an external agent process, and validating that the model represents your
workflow are further steps.

## Compare live Claude Code and Codex

Install the Claude Code and Codex CLIs and configure each with an authorized
model route. Claude Code runs in bare, tool-free mode and requires credentials
available to that mode. Remove the `policies` field from the workflow JSON.
The workflow states, action names, goal and deadline remain the experiment
definition.

```sh
plugins/exoverse/bin/exoverse-plugin workflow live workflow.json \
  --allow-model-calls --max-calls 8 --out live-evidence.json
plugins/exoverse/bin/exoverse-plugin workflow verify live-evidence.json \
  --sha256 ORIGINAL_FINGERPRINT
```

Set the invocation cap to at least twice `max_steps`. The cap limits CLI
invocations, not provider tokens, internal retries or charges. Exoverse
launches a fresh action-selection session per step in a temporary directory
dedicated to each arm. The agents receive the declared state, legal actions,
prior trajectory and success criterion. The workflow interpreter accepts
only an allowed action. Claude Code runs without tools or MCP servers. Codex
runs with the shell and web search disabled and the read-only sandbox selected.
The workflow is isolated from the model processes by this action interface.
These adapters use your installed CLIs and credentials. They do not place
the native CLIs in Exoverse-managed containers.

If a CLI fails, times out, or returns an invalid action, the run exits with
an error before writing scored evidence. The verifier checks the original
fingerprint and replays the recorded actions offline. Replay verifies the
trajectory and scores, while authentication of the originating model output
requires separate provider evidence.
