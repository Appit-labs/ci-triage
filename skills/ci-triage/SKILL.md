---
name: ci-triage
description: Find why CI failed and print only the failing lines — resolves the repo and branch, picks the newest failed GitHub Actions run or GitLab pipeline, names the failing step, and extracts the error from a log that is usually thousands of lines. Use when CI is red, a pipeline failed, a PR check is blocking, or the user asks why a build failed.
allowed-tools:
  - Bash
  - Read
permissions:
  - shell
  - env
---

# CI triage

One command goes from "CI is red" to the error text. The expensive part of CI
debugging is not reading the error — it is finding it inside 10k lines of install
noise, and that is what gets cut.

```
python3 "$SKILL_DIR/scripts/ci.py" failing [--branch BR] [--repo OWNER/NAME] [--lines 40]
```

Output shape: the run/pipeline URL, the failing job, the exact failing step, then
the extracted error block. Full log stays on the provider; only the block enters
your context.

## Portability

Works in any agent that can run shell commands (pi, Claude Code, Codex, Cursor,
Gemini CLI, …): the instructions are plain Markdown and the helper is a stdlib
script. Commands use `$SKILL_DIR` for this skill's own directory — the folder that
holds this `SKILL.md`. Set it once per session, for example:

```bash
SKILL_DIR=~/.claude/skills/ci-triage     # or ~/.codex/skills/…, ~/.pi/agent/skills/…, .cursor/skills/…
```

## Prerequisites

- **GitHub:** `gh` installed and authenticated (`gh auth status`). Needs `repo`
  scope for private repos.
- **GitLab:** `glab` installed and authenticated (`glab auth status`).
- Origin is read from `git remote get-url origin`; a URL containing `gitlab` picks
  the GitLab path, anything else GitHub. Override with `--repo owner/name`.
- Nothing else: the script is stdlib Python, no packages.

## Commands

| Need | Command |
| --- | --- |
| why is my branch red | `failing` (branch from `HEAD`, override with `--branch`) |
| dig into one GitHub job | `logs --job <job-id>` |
| dig into one GitLab job | `logs --job <job-id>` |
| already have a log file | `extract path/to/log.txt --lines 60` |
| more or less context | `--lines 40` (default), `--lines 120` for a stack trace |

## How to read the result

- The **failing step name is the first fact worth having**: `Test`, `Typecheck`,
  `Lint`, `Build`, or `Deploy` send you to different places.
- Signature → cause, fastest path:
  - `E   AssertionError` / `FAILED tests/…` → open that test and the code it
    touches; run it locally, do not re-read the log.
  - `error TS####` → typecheck, the file is in the message.
  - `npm ERR!` / lockfile / `ERESOLVE` → dependency drift, not your change.
  - `exceeded` + timeout → flaky or genuinely slow; look at what the step waited on.
  - `permission denied` / `401` / `403` → credential or token scope, not code.
- **Do not download full logs to grep them yourself.** `extract` already does it,
  and a raw log will blow out the context window.
- If the newest failed run is not the one you care about (older branch), pass
  `--branch`; the script only looks at the last 10 runs on one branch.

## Reproduce, then fix

1. Run the failing step's command locally, exactly as written.
2. If it passes locally and fails in CI, the difference is environment: the CI
   Node/Python version, an env var, a service container, or a secret. Say that
   plainly instead of re-running the pipeline repeatedly.
3. Only re-run CI after you have a reason to believe the cause is gone. A blind
   re-run is how a flaky test becomes somebody else's problem.

## Limits

- GitHub job logs for private repos need `repo` scope; logs of runs older than
  the retention window return an error, which the script surfaces verbatim.
- Self-hosted runners with restricted log streaming may return an empty body; in
  that case use the run URL.
- `failing` reports the first two failed jobs, not all of them: fix the first,
  re-run, and the rest usually disappear.
