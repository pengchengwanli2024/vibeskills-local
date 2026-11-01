"""Boundary tests; these fixtures do not replace the live-host export."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("exporter", Path(__file__).with_name("export_enabled_skills.py"))
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)


class InventoryBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root/".codex"
        self.skills = self.home/"skills"
        self.path = self.skills/"fixture/SKILL.md"
        self.path.parent.mkdir(parents=True)
        self.path.write_text("---\nname: fixture\n---\nFixture only.\n")
        self.row = {"name": "fixture", "description": "Fixture only", "path": str(self.path), "enabled": True, "scope": "user"}
        self.entry = {"resolved_skill_file": str(self.path), "active": True, "enabled": True,
                      "content_sha256": hashlib.sha256(self.path.read_bytes()).hexdigest(), "explicit_only": False}
        self.plugins = {"marketplaces": [], "marketplaceLoadErrors": []}

    def result(self, row=None, entries=None, diagnostics=None):
        return exporter.reconcile({"data": [{"skills": [row or self.row], "errors": []}]}, self.plugins,
                                  {"skills": entries if entries is not None else [self.entry],
                                   "discovery_diagnostics": diagnostics or {}}, [self.skills], self.home)

    def test_enabled_requires_current_matching_hash(self):
        self.assertEqual(self.result()["skills"][0]["binding_status"], "bindable")
        self.path.write_text("changed")
        self.assertEqual(self.result()["skills"][0]["binding_status"], "stale")

    def test_disabled_never_bindable(self):
        row = dict(self.row, enabled=False)
        result = self.result(row=row)
        self.assertEqual(result["skills"][0]["binding_status"], "disabled")
        self.assertEqual(result["summary"]["host_enabled"], 0)

    def test_multiple_active_matches_are_ambiguous(self):
        self.assertEqual(self.result(entries=[self.entry, dict(self.entry)])["skills"][0]["binding_status"], "ambiguous")

    def test_discovery_ambiguity_never_becomes_bindable(self):
        d = {"invalid_entries": [{"reason": "ambiguous_plugin_skill_id", "path": str(self.path)}]}
        self.assertEqual(self.result(diagnostics=d)["skills"][0]["binding_status"], "ambiguous")

    def test_symlink_escape_is_not_read_or_bound(self):
        outside = self.root/"outside.md"
        outside.write_text("outside-root private fixture")
        self.path.unlink()
        self.path.symlink_to(outside)
        skill = self.result()["skills"][0]
        self.assertEqual(skill["binding_status"], "invalid_source")
        self.assertIsNone(skill["content_sha256"])

    def test_host_errors_fail_closed(self):
        for payload in ({}, {"data": []}, {"data": [{"skills": [], "errors": ["failed"]}]}):
            with self.assertRaises(ValueError):
                exporter.host_rows(payload)

    def test_invalid_native_enabled_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            exporter.host_rows({"data": [{"skills": [dict(self.row, enabled="true")], "errors": []}]})

    def test_missing_index_does_not_fake_binding(self):
        self.assertEqual(self.result(entries=[])["skills"][0]["binding_status"], "not_indexed")

    def test_cached_inactive_version_is_not_binding_truth(self):
        p = self.home/"plugins/cache/market/plugin/9.9/skills/fixture/SKILL.md"
        p.parent.mkdir(parents=True)
        p.write_text("cache is not activation")
        row = dict(self.row, path=str(p))
        entry = dict(self.entry, resolved_skill_file=str(p), content_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        result = exporter.reconcile({"data": [{"skills": [row], "errors": []}]}, self.plugins,
                                    {"skills": [entry]}, [self.home/"plugins/cache"], self.home)
        self.assertEqual(result["skills"][0]["binding_status"], "invalid_source")

    def test_unreported_cache_files_do_not_enter_inventory(self):
        cached = self.home/"plugins/cache/inactive/SKILL.md"
        cached.parent.mkdir(parents=True)
        cached.write_text("not reported by host")
        self.assertEqual(self.result()["summary"]["total"], 1)
        self.assertNotIn(str(cached), str(self.result()["skills"]))


if __name__ == "__main__":
    unittest.main()
