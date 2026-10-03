# Changelog

## Unreleased

- Add canonical record fingerprints, integrity verification, bounded inspection, and redacted handoff diffs.
- Add `--require-fingerprint` so CI can reject legacy unbound records and bump the source candidate to 0.2.0.
- Reject unsupported top-level fields and non-string list members before reporting a resume fingerprint as verified.

## 0.1.0 - 2026-09-30

Initial focused release with a stable CLI contract and synthetic demo.
