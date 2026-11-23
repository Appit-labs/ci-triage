# ci-triage

<h3 align="center">CI is red → the failing step and the four lines that matter. GitHub Actions and GitLab.</h3>

<p align="center">
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/license-MIT-3DA639?style=flat-square"></a>
  <img alt="agents" src="https://img.shields.io/badge/works%20in-pi%20%7C%20Claude%20Code%20%7C%20Codex%20%7C%20Cursor-4B5563?style=flat-square">
  <img alt="skillspector" src="https://img.shields.io/badge/SkillSpector-0%2F100%20SAFE-2EA043?style=flat-square">
  <img alt="cost" src="https://img.shields.io/badge/session%20cost-~85%20tok-6E7681?style=flat-square">
</p>

<p align="center">
  <img alt="ci-triage demo — real run, regenerable from demos/ci-triage.json" src="skills/ci-triage/assets/demo.gif" width="900">
</p>

## What it is

`ci-triage` is a **log reader that knows how CI works**. Given a repo and branch, it asks the
provider which run failed, finds the job and the step inside it that broke, downloads that job's log,
throws away install noise, ANSI colour and timestamps, and prints the error block with two lines of
context around each hit. For GitLab it takes the same path through pipelines and job traces.

## The problem it removes

The expensive part of a red pipeline is not reading the error — it is finding it inside ten
thousand lines of package installation, and then not blowing up your context window with the rest. A
typical run of this turns a 10,247-line log into four lines plus the name of the failing step.

## Install

```bash
# any agent, via the skills CLI — this one, or all twelve at once
npx skills add Appit-labs/ci-triage -g -y
npx skills add Appit-labs/appit-skills -g -y

# Claude Code — the whole collection as one marketplace
claude plugin marketplace add Appit-labs/appit-skills
claude plugin install ci-triage@appit-skills

# pi
pi install git:github.com/Appit-labs/ci-triage

# any agent that reads a skills directory
git clone git@github.com:Appit-labs/ci-triage.git
cp -r ci-triage/skills/ci-triage ~/.claude/skills/      # or ~/.codex/skills/, .cursor/skills/, …
```

> **npm name.** `ci-triage` on npm belongs to another author. This skill is published as
> `@appitlabs/ci-triage`, and the whole collection as `@appitlabs/skills`.

## Use

- **Why is my branch red** — `scripts/ci.py failing` — resolves repo, branch, newest failed run, failing step, error
- **One specific job** — `scripts/ci.py logs --job <id>`
- **A log you already have** — `scripts/ci.py extract path/to/log.txt --lines 60`

## What it does not do

- It does not fix anything, and it does not re-run the pipeline for you.
- It does not download the full log into the conversation — that is the thing it exists to avoid.

## Requires

- `gh` authenticated (`gh auth status`) and/or `glab` authenticated, whichever host the repo is on.
- `repo` scope for private GitHub repos.
- Python 3.9+ (stdlib only).

## Cost

| | tokens |
| --- | --- |
| always-on — the description, paid every session | ~85 |
| on invoke | ~0.9k |

The demo above is not a mockup: `demos/ci-triage.json` holds the captured run and
`tools/make_demo.py` renders it, so it can be regenerated and audited.

## Provenance

Every command in this skill was run against a real target before it was written down: a live
database, a staging host, a failing CI run, a browser session. The repository was created and
published on 2026-11-18; where the workflow itself is older, `CHANGELOG.md` carries the dates.

## Security

SkillSpector: **0/100, SAFE, 0 open findings** against the committed baseline. Every accepted
finding is listed with its reason in [SECURITY.md](SECURITY.md). No `shell=True`, no credential
storage, no network destination chosen at runtime.

## Part of the Appit collection

All twelve, one install: `npx skills add Appit-labs/appit-skills -g -y`.

- [`live-qa`](https://github.com/Appit-labs/live-qa) — live QA in a real browser
- [`ci-triage`](https://github.com/Appit-labs/ci-triage) — red CI to the failing line ← this skill
- [`pg-inspect`](https://github.com/Appit-labs/pg-inspect) — read-only Postgres inspection
- [`repo-runbook`](https://github.com/Appit-labs/repo-runbook) — the verified runbook in AGENTS.md
- [`remote-exec`](https://github.com/Appit-labs/remote-exec) — SSH that cannot hang
- [`trello-tickets`](https://github.com/Appit-labs/trello-tickets) — seven ticket types, one card
- [`cloud-browser`](https://github.com/Appit-labs/cloud-browser) — hosted browsers that stop billing
- [`open-design`](https://github.com/Appit-labs/open-design) — the OpenDesign monorepo
- [`blender-pipeline`](https://github.com/Appit-labs/blender-pipeline) — Blender via MCP
- [`code-scan`](https://github.com/Appit-labs/code-scan) — Skylos + Fallow, one gate
- [`release`](https://github.com/Appit-labs/release) — conventional commits to a tag
- [`hermes-setup`](https://github.com/Appit-labs/hermes-setup) — least-privilege agent wiring


## License

MIT, copyright Appit Labs. See [LICENSE](LICENSE).
