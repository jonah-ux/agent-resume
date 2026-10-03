import contextlib
import io
import json
from pathlib import Path
import tempfile

from agent_resume.cli import _fingerprint, main


FIXTURE = Path(__file__).parent / "../conformance/agent-systems-lab.json"


def run_cli(*args):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(list(args))
    text = output.getvalue()
    return code, json.loads(text) if text.lstrip().startswith("{") else text


def base_record():
    record = {
        "schema": "agent-resume/v1",
        "goal": "ship synthetic review",
        "repository": "fixture-repository",
        "branch": "main",
        "commit": "fixture-commit",
        "completed": ["build"],
        "pending": ["publish"],
        "evidence": [],
        "unknowns": [],
    }
    record["fingerprint"] = _fingerprint(record)
    return record


def test_manifest_pins_native_owner_and_shared_adapter():
    manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert manifest["schema"] == "agent-systems-lab-resume-conformance/v1"
    assert manifest["owner"] == "agent-resume"
    assert manifest["native_schema"] == "agent-resume/v1"
    assert manifest["shared_adapter"]["schema"] == "agent-proof/interop/v1"
    assert len(manifest["cases"]) == 4
    assert manifest["privacy"]["evidence_content_exported"] is False


def test_fingerprint_and_tamper_states_match_the_owner_contract():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "resume.json"
        path.write_text(json.dumps(base_record()), encoding="utf-8")
        code, valid = run_cli("validate", str(path), "--require-fingerprint")
        assert code == 0
        assert valid["integrity"] == "verified"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["pending"] = ["publish", "announce"]
        path.write_text(json.dumps(record), encoding="utf-8")
        code, invalid = run_cli("validate", str(path), "--require-fingerprint")
        assert code == 1
        assert invalid["integrity"] == "mismatch"


def test_diff_exports_only_changed_field_and_digest():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        baseline = base_record()
        current = json.loads(json.dumps(baseline))
        current["pending"] = ["publish", "announce"]
        current["fingerprint"] = _fingerprint(current)
        baseline_path = root / "baseline.json"
        current_path = root / "current.json"
        baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
        current_path.write_text(json.dumps(current), encoding="utf-8")
        code, diff = run_cli("diff", str(current_path), "--against", str(baseline_path), "--require-fingerprint")
        assert code == 1
        assert diff["schema"] == "agent-resume/diff/v1"
        assert [item["field"] for item in diff["changed"]] == ["pending"]
        assert set(diff["changed"][0]) == {"field", "baseline_sha256", "current_sha256"}
