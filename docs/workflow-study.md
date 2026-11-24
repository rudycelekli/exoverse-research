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
