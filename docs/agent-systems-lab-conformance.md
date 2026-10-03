# Agent Systems Lab resume conformance

Agent Resume remains the owner of `agent-resume/v1`. This fixture and test make
its continuation boundary explicit without importing Agent Proof at runtime.

The owner proves that identity is required, canonical fingerprints bind the
record bytes, and tampering fails closed. A diff envelope carries the current
and baseline input paths and whole-record fingerprints; each `changed[]` entry
exposes only its field name and baseline/current SHA-256 values. The manifest
records Agent Proof's existing
`agent-proof/interop/v1` adapter as the downstream handoff owner; it does not
create a second registry or copy evidence text.

Run `python3 -m unittest discover -s tests` or the focused conformance test from
a fresh checkout. All data is synthetic and local.
