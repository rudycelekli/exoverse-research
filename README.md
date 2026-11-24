# Exoverse Research

**An open-source experiment workbench for AI research.** Turn a question into a controlled comparison and get evidence someone else can replay. Use it from Claude Code, Codex, or the command line.

Exoverse is built for people who want to answer their own research questions. Start with a built-in study, change one variable, and get matched results, a Markdown paper draft, and a fingerprint a reviewer can use to verify both. The built-in studies run locally with Python and require no model key.

[Install in your agent](#start-here) · [Run the demo without an agent](#see-a-study-in-action) · [Try your own comparison](docs/first-study.md)

## Run an RL environment in your browser

Open [first-environment.html](examples/browser/first-environment.html) from your downloaded source folder. Choose **Run both policies** to see each step, action and reward. Download the evidence and verify it in a second browser window using the original fingerprint. The page is self-contained and runs offline without an agent account.

## Start here

1. Open a new empty project folder. You'll need Claude Code or Codex CLI and Python 3.9 or newer. Check Python with `python3 --version`.
2. Install the plugin with the commands for your host below. Open a new session in the same project.
3. Paste this into your agent.

   > Run my first Exoverse starter study without a prediction. Use the installed Exoverse tool. Tell me what the study compared, what it measured, and what I can conclude from this simulation.

### Claude Code

```sh
claude plugin marketplace add https://github.com/rudycelekli/exoverse-research.git
claude plugin install exoverse@exoverse-research
```

### Codex CLI

```sh
codex plugin marketplace add https://github.com/rudycelekli/exoverse-research.git
codex plugin add exoverse@exoverse-research
```

Your first result compares two ways of exploring in a simulation. If your agent asks for a **prediction**, it means what you expect to see before looking at the result. The starter lets you skip it. Your guess has no effect on the measurements.

The plugin's tools run offline after install. If your agent needs a sign-in or can't see the plugin, use the direct, account-free commands in the trial guide.

## See a study in action

**Can a monitor catch false completion reports?** Give two rules the same eight simulated reports. The first flags recorded activity. The second checks the reported total against the completion ledger.

| Alert rule | Incorrect reports caught | Honest reports flagged |
| --- | ---: | ---: |
| Activity | 3 of 4 | 3 of 4 |
| Ledger check | 4 of 4 | 0 of 4 |

This is a calibration on scripted cases. The ledger rule and the ground truth both use the completion record. To see the method, case-level evidence, and paper draft, run the demo locally:

```sh
git clone https://github.com/rudycelekli/exoverse-research.git
cd exoverse-research
sh examples/replay-alignment-study.sh
```

The command prints where it saved `study.json` and `paper.md`. It checks the evidence against the example's original fingerprint and reruns the study in a separate folder. If you downloaded the release ZIP, the [advanced examples](docs/advanced.md) show the equivalent study and verification commands.

## Run your own comparison

The [first-study trial guide](docs/first-study.md) takes you from a question to an experiment with one change, a short paper draft, and a check in a second project. If someone invited you to try Exoverse, use the [feedback template](docs/trial-feedback.md) to tell them where you got stuck.

See [advanced examples](docs/advanced.md) for monitoring incorrect completion reports, independent local review, and the optional iFixAI and Ruflo adapters.

## Bring your own data and workflows

The 0.6.7 candidate can analyze matched scores, score supplied answers against
a locked reference key, collect paired outputs from local Ollama, and verify
the complete experiment. See the [model experiment guide](docs/model-experiments.md) for commands. Start with the [workflow study guide](docs/workflow-study.md)
to model a workflow with its own actions and success criteria. Run it with
scripted policies or compare action choices from installed Claude Code and Codex.

## Version and license

[Exoverse Research 0.6.6](https://github.com/rudycelekli/exoverse-research/releases/tag/v0.6.6) is released under Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). The release page provides the ZIP and its checksum. The package manifest records the contents of that ZIP.
