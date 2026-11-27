# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""Self-tests of the verdict logic of ci/mfd_ci.py (no repository data is read)."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mfd_ci as m


class T(unittest.TestCase):
    def mk(self):
        d = tempfile.mkdtemp(prefix="mfdci_t_")
        return m.Check("CI-X", "t", d, os.path.join(d, "o"))

    def test_empty_is_blocked_not_pass(self):
        self.assertEqual(self.mk().verdict(), "BLOCKED")

    def test_order_of_severity(self):
        c = self.mk()
        c.add("a", "PASS"); self.assertEqual(c.verdict(), "PASS")
        c.add("b", "PARTIAL"); self.assertEqual(c.verdict(), "PARTIAL")
        c.add("c", "BLOCKED"); self.assertEqual(c.verdict(), "BLOCKED")
        c.add("d", "FAIL"); self.assertEqual(c.verdict(), "FAIL")

    def test_overall_rules(self):
        ok = [{"id": "CI-0%d" % i, "verdict": "PASS"} for i in range(1, 6)]
        self.assertEqual(m.overall(ok + [dict(m.CI06)]), "PARTIAL")          # held CI-06 never gives PASS
        self.assertEqual(m.overall(ok[:-1] + [{"id": "CI-05", "verdict": "BLOCKED"}, dict(m.CI06)]), "BLOCKED")
        self.assertEqual(m.overall(ok[:-1] + [{"id": "CI-05", "verdict": "FAIL"}, dict(m.CI06)]), "FAIL")
        self.assertEqual(m.overall(ok + [{"id": "CI-06", "verdict": "PASS"}]), "PASS")

    def test_manifest_parser_rejects_unsafe(self):
        d = tempfile.mkdtemp(prefix="mfdci_t_")
        p = os.path.join(d, "m.txt")
        open(p, "w").write("%s  ../x\n" % ("0" * 64))
        with self.assertRaises(ValueError):
            m.parse_manifest(p)
        open(p, "w").write("nothex  a\n")
        with self.assertRaises(ValueError):
            m.parse_manifest(p)


if __name__ == "__main__":
    unittest.main()
