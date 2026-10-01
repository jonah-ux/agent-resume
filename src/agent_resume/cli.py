"""Portable, integrity-bound continuation records for agent handoffs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

VERSION = "0.2.0"
SCHEMA = "agent-resume/v1"
LIST_FIELDS = ("completed", "pending", "evidence", "unknowns")
IDENTITY_FIELDS = ("goal", "repository", "branch", "commit")
PAYLOAD_FIELDS = ("schema", *IDENTITY_FIELDS, *LIST_FIELDS)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _empty_record(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "goal": args.goal or "",
        "repository": args.repository or "",
        "branch": args.branch or "",
        "commit": args.commit or "",
        "completed": [],
        "pending": [],
        "evidence": [],
        "unknowns": [],
    }


def _payload(record: dict[str, Any]) -> dict[str, Any]:
    return {field: record.get(field, [] if field in LIST_FIELDS else "") for field in PAYLOAD_FIELDS}


def _fingerprint(record: dict[str, Any]) -> str:
    return _sha256(_canonical(_payload(record)))


def _load(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("resume record root must be a JSON object")
    return value


def _validate_record(record: dict[str, Any], *, require_fingerprint: bool = False) -> tuple[list[str], str | None, str]:
    errors: list[str] = []
    if record.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    for field in IDENTITY_FIELDS:
        if not isinstance(record.get(field), str) or not record[field].strip():
            errors.append(f"{field} is required")
    for field in LIST_FIELDS:
        if not isinstance(record.get(field), list):
            errors.append(f"{field} must be an array")

    expected = _fingerprint(record) if not errors else None
    actual = record.get("fingerprint")
    if actual is None:
        integrity = "unbound"
        if require_fingerprint:
            errors.append("fingerprint is required")
    elif not isinstance(actual, str) or actual != expected:
        integrity = "mismatch"
        errors.append("fingerprint does not match canonical record content")
    else:
        integrity = "verified"
    return errors, expected, integrity


def _validation(record: dict[str, Any], *, require_fingerprint: bool = False) -> dict[str, Any]:
    errors, fingerprint, integrity = _validate_record(record, require_fingerprint=require_fingerprint)
    return {
        "schema": "agent-resume/validation/v1",
        "ok": not errors,
        "fingerprint": fingerprint,
        "integrity": integrity,
        "errors": errors,
        "reason": "valid" if not errors else "; ".join(errors),
    }


def _digest_value(value: Any) -> str:
    return _sha256(_canonical(value))


def _diff(current: dict[str, Any], baseline: dict[str, Any], current_path: str, baseline_path: str) -> dict[str, Any]:
    changed = []
    for field in PAYLOAD_FIELDS:
        current_digest = _digest_value(current.get(field, [] if field in LIST_FIELDS else ""))
        baseline_digest = _digest_value(baseline.get(field, [] if field in LIST_FIELDS else ""))
        if current_digest != baseline_digest:
            changed.append({"field": field, "baseline_sha256": baseline_digest, "current_sha256": current_digest})
    return {
        "schema": "agent-resume/diff/v1",
        "match": not changed,
        "current": {"path": current_path, "fingerprint": _fingerprint(current)},
        "baseline": {"path": baseline_path, "fingerprint": _fingerprint(baseline)},
        "changed": changed,
    }


def _render(record: dict[str, Any], validation: dict[str, Any]) -> str:
    lines = [
        f"Agent Resume {VERSION}",
        f"goal: {record.get('goal', '')}",
        f"source: {record.get('repository', '')}@{record.get('branch', '')} ({record.get('commit', '')})",
        f"integrity: {validation['integrity']}",
        f"fingerprint: {validation['fingerprint'] or 'unavailable'}",
        f"completed: {len(record.get('completed', []))}; pending: {len(record.get('pending', []))}; evidence: {len(record.get('evidence', []))}; unknowns: {len(record.get('unknowns', []))}",
    ]
    if validation["errors"]:
        lines.append("errors: " + "; ".join(validation["errors"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-resume")
    parser.add_argument("command", choices=["create", "inspect", "validate", "diff", "render"])
    parser.add_argument("path", nargs="?", help="record path; defaults to resume.json")
    parser.add_argument("--out", default="resume.json")
    parser.add_argument("--against", help="baseline record path for diff")
    parser.add_argument("--require-fingerprint", action="store_true")
    parser.add_argument("--goal")
    parser.add_argument("--repository")
    parser.add_argument("--branch")
    parser.add_argument("--commit")
    args = parser.parse_args(argv)

    if args.command == "create":
        record = _empty_record(args)
        record["fingerprint"] = _fingerprint(record)
        destination = Path(args.out)
        destination.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record, indent=2))
        return 0

    path = args.path or args.out
    try:
        record = _load(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"schema": "agent-resume/error/v1", "ok": False, "error": str(exc)}, indent=2))
        return 2

    validation = _validation(record, require_fingerprint=args.require_fingerprint)
    if args.command == "validate":
        print(json.dumps(validation, indent=2))
        return 0 if validation["ok"] else 1
    if args.command == "render":
        print(_render(record, validation))
        return 0 if validation["ok"] else 1
    if args.command == "inspect":
        print(json.dumps({
            "schema": "agent-resume/inspect/v1",
            "ok": validation["ok"],
            "integrity": validation["integrity"],
            "fingerprint": validation["fingerprint"],
            "identity": {field: record.get(field, "") for field in IDENTITY_FIELDS},
            "counts": {field: len(record.get(field, [])) if isinstance(record.get(field, []), list) else 0 for field in LIST_FIELDS},
            "errors": validation["errors"],
        }, indent=2))
        return 0 if validation["ok"] else 1
    if args.command == "diff":
        if not args.against:
            print(json.dumps({"schema": "agent-resume/error/v1", "ok": False, "error": "--against is required for diff"}, indent=2))
            return 2
        try:
            baseline = _load(args.against)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(json.dumps({"schema": "agent-resume/error/v1", "ok": False, "error": str(exc)}, indent=2))
            return 2
        baseline_validation = _validation(baseline, require_fingerprint=args.require_fingerprint)
        if not validation["ok"] or not baseline_validation["ok"]:
            print(json.dumps({"schema": "agent-resume/error/v1", "ok": False, "current": validation, "baseline": baseline_validation}, indent=2))
            return 1
        result = _diff(record, baseline, path, args.against)
        print(json.dumps(result, indent=2))
        return 0 if result["match"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
