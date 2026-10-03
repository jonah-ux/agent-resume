import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from agent_resume.cli import _fingerprint, main


FIXTURE = Path(__file__).parent / "../conformance/agent-systems-lab.json"


class AgentSystemsLabConformanceTests(unittest.TestCase):
    def run_cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(list(args))
        text = output.getvalue()
        return code, json.loads(text) if text.lstrip().startswith("{") else text

    def base_record(self):
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

    def write_record(self, directory, record, name="resume.json"):
        path = Path(directory) / name
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def test_manifest_pins_native_owner_and_shared_adapter(self):
        manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "agent-systems-lab-resume-conformance/v1")
        self.assertEqual(manifest["owner"], "agent-resume")
        self.assertEqual(manifest["native_schema"], "agent-resume/v1")
        self.assertEqual(manifest["shared_adapter"]["schema"], "agent-proof/interop/v1")
        self.assertEqual(len(manifest["cases"]), 4)
        self.assertFalse(manifest["privacy"]["evidence_content_exported"])
        self.assertEqual(
            manifest["privacy"]["diff_exports"],
            "input_paths_and_record_fingerprints_plus_changed_field_digests",
        )

    def test_fingerprint_and_tamper_states_match_the_owner_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_record(directory, self.base_record())
            code, valid = self.run_cli("validate", str(path), "--require-fingerprint")
            self.assertEqual(code, 0)
            self.assertEqual(valid["integrity"], "verified")
            record = json.loads(path.read_text(encoding="utf-8"))
            record["pending"] = ["publish", "announce"]
            path.write_text(json.dumps(record), encoding="utf-8")
            code, invalid = self.run_cli("validate", str(path), "--require-fingerprint")
            self.assertEqual(code, 1)
            self.assertEqual(invalid["integrity"], "mismatch")

    def test_missing_identity_fields_are_rejected(self):
        for field in ("goal", "repository", "branch", "commit"):
            with self.subTest(field=field):
                record = self.base_record()
                record.pop(field)
                record["fingerprint"] = _fingerprint(record)
                with tempfile.TemporaryDirectory() as directory:
                    path = self.write_record(directory, record)
                    code, result = self.run_cli("validate", str(path), "--require-fingerprint")
                self.assertEqual(code, 1)
                self.assertFalse(result["ok"])
                self.assertIn(f"{field} is required", result["errors"])

    def test_unbound_record_requires_fingerprint_when_requested(self):
        record = self.base_record()
        record.pop("fingerprint")
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_record(directory, record)
            code, result = self.run_cli("validate", str(path), "--require-fingerprint")
        self.assertEqual(code, 1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["integrity"], "unbound")
        self.assertIn("fingerprint is required", result["errors"])

    def test_diff_exports_changed_field_digests_and_declared_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = self.base_record()
            evidence_marker = "synthetic-evidence-body-marker"
            baseline["evidence"] = [evidence_marker]
            baseline["fingerprint"] = _fingerprint(baseline)
            current = json.loads(json.dumps(baseline))
            current["pending"] = ["publish", "announce"]
            current["fingerprint"] = _fingerprint(current)
            baseline_path = self.write_record(directory, baseline, "baseline.json")
            current_path = self.write_record(directory, current, "current.json")
            code, diff = self.run_cli(
                "diff", str(current_path), "--against", str(baseline_path), "--require-fingerprint"
            )
        self.assertEqual(code, 1)
        self.assertEqual(diff["schema"], "agent-resume/diff/v1")
        self.assertEqual(set(diff), {"schema", "match", "current", "baseline", "changed"})
        self.assertFalse(diff["match"])
        self.assertEqual([item["field"] for item in diff["changed"]], ["pending"])
        self.assertEqual(set(diff["changed"][0]), {"field", "baseline_sha256", "current_sha256"})
        self.assertEqual(diff["current"], {"path": str(current_path), "fingerprint": current["fingerprint"]})
        self.assertEqual(diff["baseline"], {"path": str(baseline_path), "fingerprint": baseline["fingerprint"]})
        self.assertNotIn(evidence_marker, json.dumps(diff))
