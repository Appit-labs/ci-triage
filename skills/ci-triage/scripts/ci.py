#!/usr/bin/env python3
"""Find the failing CI job and print only the part of the log that matters.

    ci.py failing [--repo OWNER/NAME] [--branch BR] [--pr N] [--lines 40]
    ci.py logs --job ID [--repo R] [--lines 120]      # GitHub Actions job
    ci.py logs --pipeline ID [--repo R] [--lines 120] # GitLab pipeline
    ci.py extract FILE                                # extract from a saved log
    ci.py self-test

GitHub goes through `gh`, GitLab through `glab`; whichever matches the repo's
origin is used. Output is bounded on purpose: a full log is 10k+ lines of noise.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
SIGNALS = re.compile(
    r"(##\[error\]|\bERROR\b|\bFAILED\b|\bFAIL\b|\berror:|\bfatal:|\bTraceback\b|"
    r"^\s*E\s+\w+Error|AssertionError|\bpanic:|\bTS\d{4}\b|\bnpm ERR!|"
    r"\bexit(ed)? (with )?(code )?[1-9]|✗|×|FAIL:|ERROR:|\bexceeded\b.*time)", re.I)
NOISE = re.compile(r"^\s*(##\[(group|endgroup|section|debug|command)\]|Downloading |Receiving objects|"
                   r"Resolving deltas|Already up to date|Cache (restored|not found)|Waiting |Post job cleanup|"
                   r"remote: (Enumerating|Counting))")
TS = re.compile(r"^\[?\d{4}-\d\d-\d\d[T ][\d:.]+Z?\]?\s+")


def sh(argv: list[str], timeout: int = 120) -> tuple[int, str]:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, f"{type(exc).__name__}: {exc}"
    return proc.returncode, proc.stdout + proc.stderr


def clean(text: str) -> str:
    text = ANSI.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(TS.sub("", ln) for ln in text.splitlines())


def cwd_repo() -> str:
    code, out = sh(["git", "config", "--get", "remote.origin.url"])
    if code != 0:
        return ""
    url = out.strip()
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", url)
    return m.group(1) if m else ""


def host_of(repo: str) -> str:
    code, out = sh(["git", "config", "--get", "remote.origin.url"])
    url = out.strip().lower()
    return "gitlab" if "gitlab" in url else "github"


def extract(text: str, max_lines: int = 40) -> str:
    """Keep the failure lines plus a little context, drop CI boilerplate."""
    lines = [clean(ln) for ln in text.splitlines()]
    hits = [i for i, ln in enumerate(lines) if SIGNALS.search(ln) and not NOISE.match(ln)]
    if not hits:
        tail = [ln for ln in lines if ln.strip()][-max_lines:]
        return "\n".join(tail)
    keep: list[int] = []
    for i in hits:
        keep.extend(j for j in range(max(0, i - 2), min(len(lines), i + 3))
                    if j == i or not NOISE.match(lines[j]))
    ordered = sorted(set(keep))
    out, last = [], None
    for i in ordered:
        if last is not None and i - last > 3:
            out.append("…")
        line = lines[i]
        out.append(line[:220])
        last = i
    if len(out) > max_lines:
        out = out[:max_lines - 5] + ["…"] + out[-4:]
    return "\n".join(out)


def gh_failing(repo: str, branch: str, lines: int) -> int:
    code, out = sh(["gh", "run", "list", "--repo", repo, "--branch", branch, "--limit", "10",
                    "--json", "databaseId,name,conclusion,url,headSha"])
    if code != 0:
        print(out.strip(), file=sys.stderr)
        return 1
    try:
        runs = json.loads(out or "[]")
    except ValueError:
        print("could not parse `gh run list` output", file=sys.stderr)
        return 1
    failed = [r for r in runs if str(r.get("conclusion")).lower() in {"failure", "startup_failure", "timed_out"}]
    if not failed:
        print(f"no failed runs on {branch} (last {len(runs)} checked)")
        return 0
    run = failed[0]
    print(f"run {run['databaseId']} {run.get('name')} — {run.get('conclusion')}\n{run.get('url')}")
    code, out = sh(["gh", "api", f"repos/{repo}/actions/runs/{run['databaseId']}/jobs?per_page=50"])
    try:
        jobs = json.loads(out or "{}").get("jobs", [])
    except ValueError:
        jobs = []
    bad = [j for j in jobs if str(j.get("conclusion")).lower() in {"failure", "timed_out", "cancelled"}]
    if not jobs:
        print("this run has no jobs: it failed before any step started, which is almost always a "
              "workflow file problem (bad YAML, unknown action, or a bad expression).")
        print(f"next: gh run view {run['databaseId']} --repo {repo} --log-failed   # or check annotations in the UI")
        return 1
    if not bad:
        seen = ", ".join(f"{j.get('name')}={j.get('conclusion')}" for j in jobs[:8]) or "none"
        print(f"no failed job (conclusions: {seen}); the run itself is marked {run.get('conclusion')}")
        return 0
    for job in bad[:2]:
        print(f"\n== job {job['id']} {job['name']}")
        step = next((s["name"] for s in job.get("steps", []) if str(s.get("conclusion")) == "failure"), "?")
        print(f"   failing step: {step}")
        code, log = sh(["gh", "api", f"repos/{repo}/actions/jobs/{job['id']}/logs"], 180)
        print(extract(log, lines))
    return 1


def glab_failing(repo: str, branch: str, lines: int) -> int:
    enc = repo.replace("/", "%2F")
    code, out = sh(["glab", "api", f"projects/{enc}/pipelines?ref={branch}&status=failed&per_page=3"])
    if code != 0:
        print(out.strip(), file=sys.stderr)
        return 1
    pipelines = json.loads(out or "[]")
    if not pipelines:
        print(f"no failed pipelines on {branch}")
        return 0
    p = pipelines[0]
    print(f"pipeline {p['id']} {p.get('status')} {p.get('web_url','')}".strip())
    code, out = sh(["glab", "api", f"projects/{enc}/pipelines/{p['id']}/jobs?per_page=50"])
    jobs = json.loads(out or "[]")
    bad = [j for j in jobs if j.get("status") == "failed"]
    if not bad:
        print("no failed job; inspect the pipeline URL")
        return 0
    for job in bad[:2]:
        print(f"\n== job {job['id']} {job['name']} (stage {job.get('stage')})")
        code, log = sh(["glab", "api", f"projects/{enc}/jobs/{job['id']}/trace"], 180)
        print(extract(log, lines))
    return 1


def main(argv: list[str]) -> int:
    opts = dict(a.lstrip("-").split("=", 1) for a in argv[1:] if a.startswith("--") and "=" in a)
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args or args[0] in {"-h", "--help", "help"}:
        print(__doc__)
        return 0
    cmd = args[0]
    if cmd == "self-test":
        return self_test()
    repo = opts.get("repo") or cwd_repo()
    lines = int(opts.get("lines", 40))
    if cmd == "extract" and len(args) > 1:
        print(extract(Path(args[1]).read_text(errors="replace"), lines))
        return 0
    if cmd == "failing":
        if not repo:
            print("no --repo and no git origin; pass --repo OWNER/NAME", file=sys.stderr)
            return 2
        branch = opts.get("branch") or os.environ.get("CI_BRANCH") or _branch()
        print(f"repo {repo} branch {branch} via {host_of(repo)}")
        return gh_failing(repo, branch, lines) if host_of(repo) == "github" else glab_failing(repo, branch, lines)
    if cmd == "logs" and opts.get("job"):
        if host_of(repo) == "github":
            code, log = sh(["gh", "api", f"repos/{repo}/actions/jobs/{opts['job']}/logs"], 180)
        else:
            code, log = sh(["glab", "api", f"projects/{repo.replace('/', '%2F')}/jobs/{opts['job']}/trace"], 180)
        print(extract(log, lines))
        return code
    print(f"unknown or incomplete command: {' '.join(args)}", file=sys.stderr)
    return 2


def _branch() -> str:
    code, out = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return out.strip() if code == 0 else "main"


def self_test() -> int:
    sample = clean("""
##[group]Run pytest
2026-01-01T00:00:01.000Z Downloading wheels...
tests/test_api.py::test_login FAILED
    E   AssertionError: expected 200 got 500
##[error]Process completed with exit code 1
""")
    out = extract(sample, 20)
    assert "AssertionError" in out and "FAILED" in out, out
    assert "2026-01-01T" not in out, "timestamps must be stripped"
    assert "Downloading wheels" not in out, out
    noise_only = "Downloading a\nReceiving objects\nstep done\nall good"
    assert extract(noise_only, 5), "must fall back to tail"
    ansi = "\x1b[31mFAIL: build\x1b[0m"
    assert extract(ansi, 5).strip() == "FAIL: build", extract(ansi, 5)
    long_line = "error: " + "x" * 500
    assert all(len(ln) <= 220 for ln in extract(long_line, 5).splitlines()), "must clamp width"
    empty = extract("", 10)
    assert empty.strip() == "", repr(empty)
    print("self-test ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
