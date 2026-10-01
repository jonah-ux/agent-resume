import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from agent_resume.cli import main


class ResumeTests(unittest.TestCase):
    def run_cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(list(args))
        return code, json.loads(output.getvalue()) if output.getvalue().lstrip().startswith("{") else output.getvalue()

    def write(self, value):
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(value, handle)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name

    def record(self, **extra):
        value = {
            "schema": "agent-resume/v1",
            "goal": "ship",
            "repository": "demo",
            "branch": "main",
            "commit": "abc123",
            "completed": ["build"],
            "pending": ["publish"],
            "evidence": [],
            "unknowns": [],
        }
        value.update(extra)
        return value

    def test_create_binds_fingerprint_and_validate_verifies_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "resume.json")
            code, created = self.run_cli("create", "--out", path, "--goal", "ship", "--repository", "demo", "--branch", "main", "--commit", "abc123")
            self.assertEqual(code, 0)
            self.assertEqual(created["schema"], "agent-resume/v1")
            self.assertEqual(len(created["fingerprint"]), 64)
            valid_code, result = self.run_cli("validate", path, "--require-fingerprint")
            self.assertEqual(valid_code, 0)
            self.assertEqual(result["integrity"], "verified")

    def test_tamper_is_rejected(self):
        record = self.record()
        record["fingerprint"] = __import__("agent_resume.cli", fromlist=["_fingerprint"])._fingerprint(record)
        record["pending"] = ["publish", "announce"]
        code, result = self.run_cli("validate", self.write(record), "--require-fingerprint")
        self.assertEqual(code, 1)
        self.assertEqual(result["integrity"], "mismatch")

    def test_diff_reports_changed_fields_and_fails_closed(self):
        baseline = self.record()
        baseline["fingerprint"] = __import__("agent_resume.cli", fromlist=["_fingerprint"])._fingerprint(baseline)
        current = json.loads(json.dumps(baseline))
        current["pending"] = ["publish", "announce"]
        current["fingerprint"] = __import__("agent_resume.cli", fromlist=["_fingerprint"])._fingerprint(current)
        code, result = self.run_cli("diff", self.write(current), "--against", self.write(baseline), "--require-fingerprint")
        self.assertEqual(code, 1)
        self.assertEqual(result["schema"], "agent-resume/diff/v1")
        self.assertEqual([item["field"] for item in result["changed"]], ["pending"])

    def test_render_and_inspect_expose_bounded_summary(self):
        record = self.record()
        record["fingerprint"] = __import__("agent_resume.cli", fromlist=["_fingerprint"])._fingerprint(record)
        path = self.write(record)
        code, result = self.run_cli("inspect", path, "--require-fingerprint")
        self.assertEqual(code, 0)
        self.assertEqual(result["counts"]["pending"], 1)
        render_code, rendered = self.run_cli("render", path, "--require-fingerprint")
        self.assertEqual(render_code, 0)
        self.assertIn("integrity: verified", rendered)


if __name__ == "__main__":
    unittest.main()
