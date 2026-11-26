#!/usr/bin/env python3
"""Regression tests of tools/verify_kit_manifest.py on SYNTHETIC mini-kits built in a temporary directory (the real kit is never modified).
Cases: normal kit, missing file, modified file, unregistered file added, unsafe path in a manifest, unreadable file (injected read error),
special file state (symbolic link; simulated cloud-placeholder attributes), path-resolution fault, file not in the allow-list, duplicate path,
unclassified file type.  A normal kit must pass (rc 0); every fault must fail with the expected finding and a non-zero exit code (never PASS).
Run: python3 -I -B tools/test_verify_kit_manifest.py"""
import os, sys, shutil, tempfile, hashlib, unittest, io, contextlib, importlib.util, stat
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vkm", os.path.join(HERE, "verify_kit_manifest.py")); vkm = importlib.util.module_from_spec(spec); sys.dont_write_bytecode = True; spec.loader.exec_module(vkm)

def sha(b): return hashlib.sha256(b).hexdigest()
def rd(p, m="rb"):
    with open(p, m) as f: return f.read()
def wr(p, d, m="w", **k):
    with open(p, m, **k) as f: f.write(d)
def build(root):
    files = {"layer1_300trial/data/a.jsonl": b'{"x":1}\n', "layer2_33traj/b.m2": b"BIN", "layer3_public_kit/c.py": b"print(1)\n",
             "layer3_public_kit/evidence_input/e.json": b"{}\n", "README.md": b"hi\n"}
    for n, b in files.items():
        p = os.path.join(root, n); os.makedirs(os.path.dirname(p), exist_ok=True); wr(p, b, "wb")
    def wm(path, base, names):
        with open(os.path.join(root, path), "w", newline="\n") as f:
            for n in sorted(names): f.write("%s  %s\n" % (sha(rd(os.path.join(root, base, n))), n))
    wm("layer3_public_kit/evidence_input/SHA256SUMS.txt", "layer3_public_kit/evidence_input", ["e.json"])
    wm("layer1_300trial/SHA256SUMS_layer1.txt", "layer1_300trial", ["data/a.jsonl"])
    wm("layer2_33traj/SHA256SUMS_layer2.txt", "layer2_33traj", ["b.m2"])
    wm("layer3_public_kit/KIT_MANIFEST_sha256.txt", "layer3_public_kit", ["c.py", "evidence_input/e.json", "evidence_input/SHA256SUMS.txt"])
    os.makedirs(os.path.join(root, "tools"), exist_ok=True)
    allow = sorted(n for n in (list(files) + ["layer1_300trial/SHA256SUMS_layer1.txt", "layer2_33traj/SHA256SUMS_layer2.txt", "layer3_public_kit/KIT_MANIFEST_sha256.txt",
                                           "layer3_public_kit/evidence_input/SHA256SUMS.txt", "tools/public_allowlist.txt"]))
    open(os.path.join(root, "tools/public_allowlist.txt"), "w", newline="\n").write("\n".join(allow) + "\n")
    top = [n for n in allow] 
    with open(os.path.join(root, "KIT_MANIFEST_sha256.txt"), "w", newline="\n") as f:
        for n in sorted(top): f.write("%s  %s\n" % (sha(rd(os.path.join(root, n))), n))

def run(root, *extra):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): rc = vkm.main(["x", root] + list(extra))
    return rc, buf.getvalue()

class T(unittest.TestCase):
    def setUp(self): self.d = tempfile.mkdtemp(prefix="vkm_"); build(self.d)
    def tearDown(self): shutil.rmtree(self.d, ignore_errors=True)
    def test_normal_kit_passes(self):
        rc, out = run(self.d); self.assertEqual(rc, 0, out); self.assertIn("KIT INTEGRITY: OK", out)
    def test_missing_file(self):
        os.remove(os.path.join(self.d, "layer3_public_kit/c.py")); rc, out = run(self.d); self.assertEqual(rc, 1); self.assertIn("NOT_FOUND", out)
    def test_modified_file(self):
        wr(os.path.join(self.d, "README.md"), b"x", "ab"); rc, out = run(self.d); self.assertEqual(rc, 1); self.assertIn("MISMATCH", out)
    def test_unregistered_file(self):
        wr(os.path.join(self.d, "layer3_public_kit/new.py"), "1", "w"); rc, out = run(self.d); self.assertEqual(rc, 1); self.assertIn("UNREGISTERED", out); self.assertIn("NOT_IN_ALLOWLIST", out)
    def test_unsafe_path_in_manifest(self):
        with open(os.path.join(self.d, "KIT_MANIFEST_sha256.txt"), "a") as f: f.write("%s  ../outside.txt\n" % sha(b"x"))
        rc, out = run(self.d); self.assertEqual(rc, 1); self.assertIn("UNSAFE_PATHS", out)
    def test_duplicate_path_in_manifest(self):
        with open(os.path.join(self.d, "KIT_MANIFEST_sha256.txt")) as f: first = f.readline()
        with open(os.path.join(self.d, "KIT_MANIFEST_sha256.txt"), "a") as f: f.write(first)
        rc, out = run(self.d); self.assertEqual(rc, 1); self.assertIn("DUPLICATE_PATHS", out)
    def test_unreadable_file_is_not_pass(self):
        target = os.path.join(self.d, "README.md"); real = open
        def fake_open(p, *a, **k):
            if os.path.abspath(str(p)) == os.path.abspath(target) and "b" in (a[0] if a else k.get("mode", "")): raise PermissionError(13, "Permission denied")
            return real(p, *a, **k)
        import builtins; builtins.open = fake_open
        try: rc, out = run(self.d)
        finally: builtins.open = real
        self.assertEqual(rc, 2); self.assertIn("UNREADABLE", out); self.assertNotIn("KIT INTEGRITY: OK", out)
    def test_symlink_is_special_state_not_pass(self):
        t = os.path.join(self.d, "README.md"); data = rd(t); os.remove(t); real = os.path.join(self.d, "real_readme.bin"); wr(real, data, "wb")
        try: os.symlink(real, t)
        except (OSError, NotImplementedError): self.skipTest("symlinks unavailable on this file system")
        rc, out = run(self.d); self.assertNotEqual(rc, 0); self.assertIn("SPECIAL_STATE", out); self.assertNotIn("KIT INTEGRITY: OK", out)
    def test_placeholder_attributes_are_special_state(self):
        target = os.path.join(self.d, "README.md"); real = os.lstat
        class S:  # a stat result carrying cloud-placeholder attributes (simulated; Windows only in reality)
            def __init__(s, st): s.st_mode = st.st_mode; s.st_file_attributes = 0x400000 | 0x400; s.st_reparse_tag = 0x9000601A
        def fake(p, *a, **k):
            st = real(p, *a, **k)
            return S(st) if os.path.abspath(str(p)) == os.path.abspath(target) else st
        os.lstat = fake
        try: rc, out = run(self.d)
        finally: os.lstat = real
        self.assertEqual(rc, 2); self.assertIn("SPECIAL_STATE", out)
    def test_path_resolution_fault_is_distinct(self):
        target = os.path.join(self.d, "README.md"); real = os.lstat
        def fake(p, *a, **k):
            if os.path.abspath(str(p)) == os.path.abspath(target): raise OSError(36, "File name too long")
            return real(p, *a, **k)
        os.lstat = fake
        try: rc, out = run(self.d)
        finally: os.lstat = real
        self.assertEqual(rc, 2); self.assertIn("PATH_RESOLUTION", out)
    def test_file_not_in_allowlist(self):
        p = os.path.join(self.d, "tools/public_allowlist.txt"); L = [l for l in open(p).read().splitlines() if l != "README.md"]; wr(p, "\n".join(L) + "\n", "w")
        rc, out = run(self.d); self.assertEqual(rc, 1); self.assertIn("NOT_IN_ALLOWLIST", out)
    def test_unclassified_file_type(self):
        wr(os.path.join(self.d, "unknown.xyz"), "x", "w"); rc, out = run(self.d); self.assertEqual(rc, 1); self.assertIn("UNCLASSIFIED", out)
    def test_allowlist_sha_external_check(self):
        rc, out = run(self.d, "--allowlist-sha", "0" * 64); self.assertEqual(rc, 1); self.assertIn("MISMATCH", out)
        good = sha(rd(os.path.join(self.d, "tools/public_allowlist.txt"))); rc, out = run(self.d, "--allowlist-sha", good); self.assertEqual(rc, 0, out)
    def test_non_ascii_file_name_is_flagged(self):
        wr(os.path.join(self.d, "layer3_public_kit/\u65e5\u672c.py"), "1"); rc, out = run(self.d); self.assertEqual(rc, 1); self.assertIn("UNSAFE_PATHS", out)
    def test_runs_output_area_is_ignored(self):
        os.makedirs(os.path.join(self.d, "runs/run1")); wr(os.path.join(self.d, "runs/run1/out.bin"), "x", "w"); rc, out = run(self.d); self.assertEqual(rc, 0, out)

if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1); sys.exit(0 if r.result.wasSuccessful() else 1)
