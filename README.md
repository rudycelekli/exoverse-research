# Exoverse Research

Run your first experiment, see what changed, and give someone else enough evidence to check your work. The built-in studies are small simulations that run on your computer.

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

## Run your own comparison

The [first-study trial guide](docs/first-study.md) takes you from a question to an experiment with one change, a short paper draft, and a check in a second project. If someone invited you to try Exoverse, use the [feedback template](docs/trial-feedback.md) to tell them where you got stuck.

See [advanced examples](docs/advanced.md) for monitoring incorrect completion reports, independent local review, and the optional iFixAI and Ruflo adapters.

## Version and license

[Exoverse Research 0.6.6](https://github.com/rudycelekli/exoverse-research/releases/tag/v0.6.6) is released under Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). The release page provides the ZIP and its checksum. The package manifest records the contents of that ZIP.
