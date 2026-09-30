# Agent Resume

![portable agent continuation records workflow](docs/header.svg)

**Make unfinished agent work safe to inspect and continue.**

[![CI](https://github.com/jonah-ux/agent-resume/actions/workflows/ci.yml/badge.svg)](https://github.com/jonah-ux/agent-resume/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)

Agent Resume stores the small set of facts a new agent needs to continue work: the goal,
repository, branch, commit, completed steps, pending steps, evidence, and unknowns. It keeps
continuation portable without pretending that a stale note is live runtime state.

## Try it in 30 seconds

```bash
python -m pip install git+https://github.com/jonah-ux/agent-resume.git@main
python demos/demo.py
```

Create and validate a continuation record:

```bash
agent-resume create --out resume.json
agent-resume validate resume.json
```

## See it work

Validation fails closed when the continuation record is missing its identity fields; a valid record is easy to hand to the next agent:

```json
{"schema":"agent-resume/validation/v1","ok":true,"reason":"valid"}
```

## Related tools

Use [Agent Proof](https://github.com/jonah-ux/agent-proof) to attach evidence, [Chatlens](https://github.com/jonah-ux/chatlens) to recover the missing conversation, and [Worktree Conservator](https://github.com/jonah-ux/worktree-conservator) to keep the repository state recoverable.

Validation requires a goal, repository identity, and commit so a handoff cannot quietly lose
which source state it describes. The record uses the `agent-resume/v1` schema.

## Development

```bash
python -m unittest discover -s tests
python -m build --sdist --wheel
python demos/demo.py
```

A resume file is a handoff aid. Re-check the repository and runtime before claiming the work is
complete.

MIT licensed.
