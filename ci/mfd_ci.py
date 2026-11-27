#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hazime Sendo
"""MFD-CI-001 verification driver (standard library only).

Re-verifies the PUBLISHED, STORED assets. It never generates a new trial or trajectory and never
touches non-public assets. Verdicts: PASS / FAIL / BLOCKED / PARTIAL. A check that did not run is never PASS.

usage: python ci/mfd_ci.py env|ci01|ci02|ci03|ci04|ci05 REPO_DIR OUT_DIR
       python ci/mfd_ci.py aggregate IN_DIR OUT_DIR
"""
import csv, datetime, hashlib, json, os, platform, re, shutil, subprocess, sys, tempfile, time

KIT = os.path.join("validation", "mfd_independent_reproduction_ready_kit_rev4")
PUBLIC_MANIFEST = "PUBLIC_MANIFEST_SHA256.txt"
CI_MANIFEST = os.path.join("ci", "CI_MANIFEST_SHA256.txt")
RANK = {"PASS": 0, "PARTIAL": 1, "BLOCKED": 2, "FAIL": 3}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_expected(repo):
    return json.load(open(os.path.join(repo, "ci", "expected.json"), encoding="utf-8"))


def commit_id(repo):
    c = os.environ.get("GITHUB_SHA")
    if c:
        return c
    try:
        return subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


class Check:
    """Collects individual checks and decides the verdict. Order: FAIL > BLOCKED > PARTIAL > PASS."""

    def __init__(self, cid, name, repo, out):
        self.cid, self.name, self.repo, self.out = cid, name, repo, out
        self.checks, self.tests, self.notes, self.files = [], [], [], {}
        self.t0 = time.time()
        os.makedirs(os.path.join(out, "logs"), exist_ok=True)

    def add(self, name, status, detail=""):
        assert status in RANK, status
        self.checks.append({"name": name, "status": status, "detail": detail})

    def run(self, label, cmd, cwd=None, env=None, timeout=900):
        """Run a command, save its log, return (rc, text). rc=None when it could not be started or timed out."""
        e = dict(os.environ)
        e["PYTHONDONTWRITEBYTECODE"] = "1"
        if env:
            e.update(env)
        try:
            p = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True, timeout=timeout, errors="replace")
            rc, text = p.returncode, (p.stdout or "") + (("\n--- stderr ---\n" + p.stderr) if p.stderr else "")
        except subprocess.TimeoutExpired:
            rc, text = None, "TIMEOUT after %s s" % timeout
        except OSError as ex:
            rc, text = None, "COULD NOT START: %s" % ex
        text = sanitize(text)
        with open(os.path.join(self.out, "logs", label + ".log"), "w", encoding="utf-8") as f:
            f.write("$ %s\nexit code: %s\n\n%s" % (" ".join(cmd), rc, text))
        return rc, text

    def verdict(self):
        v = "PASS"
        for c in self.checks:
            if RANK[c["status"]] > RANK[v]:
                v = c["status"]
        if not self.checks:
            v = "BLOCKED"
        return v

    def finish(self):
        v = self.verdict()
        res = {"id": self.cid, "name": self.name, "verdict": v, "commit": commit_id(self.repo), "finished_utc": utc(),
               "seconds": round(time.time() - self.t0, 1), "checks": self.checks, "tests": self.tests, "notes": self.notes}
        with open(os.path.join(self.out, "verdict.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1, ensure_ascii=False)
        # SHA-256 of every output file of this check (verdict.json excluded: it is the record itself)
        lines = []
        for dp, _, fs in os.walk(self.out):
            for fn in sorted(fs):
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, self.out).replace(os.sep, "/")
                if rel not in ("verdict.json", "SHA256SUMS.txt"):
                    lines.append("%s  %s" % (sha256_file(p), rel))
        with open(os.path.join(self.out, "SHA256SUMS.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(lines, key=lambda s: s.split("  ", 1)[1])) + "\n")
        print("%s %s -> %s" % (self.cid, self.name, v))
        for c in self.checks:
            print("  [%s] %s %s" % (c["status"], c["name"], c["detail"]))
        return {"PASS": 0, "PARTIAL": 0, "BLOCKED": 3, "FAIL": 1}[v]


def sanitize(text):
    """Keep evidence free of runner-specific absolute paths (workspace and temp locations)."""
    for var in ("GITHUB_WORKSPACE", "RUNNER_TEMP", "HOME"):
        val = os.environ.get(var)
        if val and len(val) > 3:
            text = text.replace(val, "<%s>" % var)
    return re.sub(r"/tmp/mfdci_[A-Za-z0-9_]+", "<work>", text)


def copy_kit(repo, work):
    dst = os.path.join(work, "kit")
    shutil.copytree(os.path.join(repo, KIT), dst)
    return dst


def parse_manifest(path):
    ents = []
    for ln, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
        if not line.strip():
            continue
        m = re.fullmatch(r"([0-9a-f]{64}) [ *](.+)", line)
        if not m:
            raise ValueError("%s line %d: format error" % (path, ln))
        rel = m.group(2)
        if rel.startswith("/") or ".." in rel.split("/") or "\\" in rel:
            raise ValueError("%s line %d: unsafe path %r" % (path, ln, rel))
        ents.append((m.group(1), rel))
    return ents


def check_manifest(c, repo, manifest, label, expected_count=None):
    try:
        ents = parse_manifest(os.path.join(repo, manifest))
    except (OSError, ValueError) as ex:
        c.add(label + ": read", "BLOCKED", str(ex))
        return set()
    seen = set()
    bad_missing, bad_hash, dup = [], [], []
    for h, rel in ents:
        if rel in seen:
            dup.append(rel)
        seen.add(rel)
        p = os.path.join(repo, rel)
        if not os.path.isfile(p):
            bad_missing.append(rel)
        elif sha256_file(p) != h:
            bad_hash.append(rel)
    c.add(label + ": every listed file present", "FAIL" if bad_missing else "PASS", "missing=%d %s" % (len(bad_missing), bad_missing[:5]))
    c.add(label + ": every SHA-256 matches", "FAIL" if bad_hash else "PASS", "mismatch=%d %s" % (len(bad_hash), bad_hash[:5]))
    c.add(label + ": no duplicate entries", "FAIL" if dup else "PASS", "duplicates=%d" % len(dup))
    if expected_count is not None:
        ok = len(ents) == expected_count
        c.add(label + ": entry count (scope unchanged)", "PASS" if ok else "FAIL", "%d (expected %d)" % (len(ents), expected_count))
    return seen


def walk_files(repo):
    out = set()
    for dp, dn, fs in os.walk(repo):
        dn[:] = [d for d in dn if d != ".git"]
        for fn in fs:
            out.add(os.path.relpath(os.path.join(dp, fn), repo).replace(os.sep, "/"))
    return out


# ---------------------------------------------------------------------------------- env
def cmd_env(repo, out):
    os.makedirs(out, exist_ok=True)
    pk = {}
    try:
        import importlib.metadata as md
        for n in ("numpy", "scipy", "matplotlib", "pytest"):
            try:
                pk[n] = md.version(n)
            except md.PackageNotFoundError:
                pk[n] = None
    except Exception:
        pass
    info = {"utc": utc(), "commit": commit_id(repo), "ref": os.environ.get("GITHUB_REF"), "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "event": os.environ.get("GITHUB_EVENT_NAME"),
            "workflow": os.environ.get("GITHUB_WORKFLOW"), "job": os.environ.get("GITHUB_JOB"),
            "runner_os": os.environ.get("RUNNER_OS"), "runner_arch": os.environ.get("RUNNER_ARCH"), "image": os.environ.get("ImageOS"),
            "image_version": os.environ.get("ImageVersion"), "python": sys.version, "platform": platform.platform(), "packages": pk}
    with open(os.path.join(out, "env.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)
    print(json.dumps(info, indent=1))
    return 0


# ---------------------------------------------------------------------------------- CI-01
def cmd_ci01(repo, out):
    c = Check("CI-01", "public asset integrity", repo, out)
    exp = load_expected(repo)
    registered = check_manifest(c, repo, PUBLIC_MANIFEST, "public manifest", exp["public_manifest_entries"])
    ci_registered = check_manifest(c, repo, CI_MANIFEST, "CI manifest")
    allowed = registered | ci_registered | {PUBLIC_MANIFEST, CI_MANIFEST}
    unreg = sorted(walk_files(repo) - allowed)
    c.add("no unregistered file in the checkout", "FAIL" if unreg else "PASS", "unregistered=%d %s" % (len(unreg), unreg[:8]))
    kit = os.path.join(repo, KIT)
    py = sys.executable
    jpath = os.path.join(out, "kit_manifest_check.json")
    rc, text = c.run("kit_verify_manifest", [py, "-I", "-B", "tools/verify_kit_manifest.py", kit, "--json", jpath], cwd=kit)
    if rc is None or rc == 2 or not os.path.isfile(jpath):
        c.add("kit verifier (237 entries)", "BLOCKED", "verifier could not verify (rc=%s)" % rc)
    else:
        counts = json.load(open(jpath)).get("counts", {})
        k = exp["kit_verifier"]
        okc = counts.get("ok") == k["ok"] and all(counts.get(z) == 0 for z in k["zero_counters"])
        c.add("kit verifier (237 entries)", "PASS" if (rc == 0 and okc) else "FAIL", "rc=%s ok=%s problems=%s" % (rc, counts.get("ok"), {z: counts.get(z) for z in k["zero_counters"] if counts.get(z)}))
        c.notes.append("kit verifier counts: %s" % counts)
    work = tempfile.mkdtemp(prefix="mfdci_")
    try:
        kc = copy_kit(repo, work)
        rc, text = c.run("kit_verifier_regression_tests", [py, "-I", "-B", "tools/test_verify_kit_manifest.py"], cwd=kc)
        m = re.search(r"Ran (\d+) tests?", text)
        n = int(m.group(1)) if m else None
        c.tests.append({"suite": "kit manifest-verifier regression tests", "exit_code": rc, "executed": n})
        if rc is None or n is None:
            c.add("verifier regression tests", "BLOCKED", "could not run or parse (rc=%s)" % rc)
        else:
            good = rc == 0 and n == exp["kit_verifier"]["regression_tests"] and re.search(r"^OK\s*$", text, re.M)
            c.add("verifier regression tests", "PASS" if good else "FAIL", "rc=%s executed=%s (expected %s)" % (rc, n, exp["kit_verifier"]["regression_tests"]))
        rc, text = c.run("ci_self_tests", [py, "-I", "-B", "-m", "unittest", "discover", "-s", os.path.join(repo, "ci"), "-p", "test_*.py"], cwd=repo)
        m = re.search(r"Ran (\d+) tests?", text)
        c.tests.append({"suite": "ci driver self-tests", "exit_code": rc, "executed": int(m.group(1)) if m else None})
        c.add("CI driver self-tests", "PASS" if (rc == 0 and m) else ("BLOCKED" if rc is None else "FAIL"), "rc=%s" % rc)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return c.finish()


# ---------------------------------------------------------------------------------- CI-02
def cmd_ci02(repo, out):
    c = Check("CI-02", "regression tests (repository)", repo, out)
    exp = load_expected(repo)
    work = tempfile.mkdtemp(prefix="mfdci_")
    try:
        rp = os.path.join(work, "repo")
        shutil.copytree(repo, rp, ignore=shutil.ignore_patterns(".git"))
        rc, text = c.run("pytest_tests", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"], cwd=rp, timeout=1500)
        m = re.search(r"(\d+) passed", text)
        passed = int(m.group(1)) if m else None
        bad = re.search(r"\b(\d+) (failed|error|errors)\b", text)
        c.tests.append({"suite": "pytest tests/", "exit_code": rc, "executed": passed, "passed": passed})
        if rc is None or (passed is None and not bad):
            c.add("pytest tests/", "BLOCKED", "could not run or parse (rc=%s)" % rc)
        else:
            good = rc == 0 and passed == exp["root_pytest_passed"] and not bad
            c.add("pytest tests/", "PASS" if good else "FAIL", "rc=%s passed=%s (expected %s)" % (rc, passed, exp["root_pytest_passed"]))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return c.finish()


# ---------------------------------------------------------------------------------- CI-03
def cmd_ci03(repo, out):
    c = Check("CI-03", "Layer I (stored 300 trials)", repo, out)
    exp = load_expected(repo)["layer1"]
    py = sys.executable
    work = tempfile.mkdtemp(prefix="mfdci_")
    try:
        kc = copy_kit(repo, work)
        data = os.path.join(kc, "layer1_300trial", "data", "dmax_sweep_runs.jsonl")
        sh = sha256_file(data)
        c.add("input SHA-256 (kit Layer I data)", "PASS" if sh == exp["input_sha256"] else "FAIL", sh[:16])
        n = sum(1 for ln in open(data, encoding="utf-8") if ln.strip())
        c.add("stored trials = 300 (no new trial generated)", "PASS" if n == exp["trials"] else "FAIL", "records=%d" % n)
        root_data = os.path.join(repo, "data", "dmax_sweep_runs.jsonl")
        c.add("repository data/ copy identical to kit copy", "PASS" if sha256_file(root_data) == sh else "FAIL", "")
        o = os.path.join(work, "layer1_out")
        os.makedirs(o)
        rc, text = c.run("layer1_clip_and_bootstrap", [py, "layer1_300trial/code/rev3_clip_and_bootstrap.py", "layer1_300trial/data/dmax_sweep_runs.jsonl", o], cwd=kc)
        c.tests.append({"suite": "Layer I analysis run", "exit_code": rc, "executed": None})
        if rc is None:
            c.add("Layer I analysis (re-aggregation)", "BLOCKED", "could not run")
        else:
            m = re.search(r"A: (\d+) cells x (\d+) trials", text)
            b = re.search(r"B: replicates (\d+); inestimable \(a,replicate\) fits: (\d+)", text)
            good = rc == 0 and m and int(m.group(1)) == exp["cells"] and b and int(b.group(1)) == exp["bootstrap_replicates"] and int(b.group(2)) == 0
            c.add("Layer I analysis (re-aggregation)", "PASS" if good else "FAIL", "rc=%s cells=%s replicates=%s inestimable=%s" % (rc, m and m.group(1), b and b.group(1), b and b.group(2)))
        rc2, text2 = c.run("layer1_expected_check", [py, "tools/check_layer1_expected.py", o, "expected/layer1_expected.json"], cwd=kc)
        okline = re.search(r"clip ratio cell means: n=30 .* -> OK", text2 or "")
        if rc2 is None:
            c.add("clip-ratio check against stored expectation", "BLOCKED", "could not run")
        else:
            c.add("clip-ratio check against stored expectation", "PASS" if (rc2 == 0 and okline) else "FAIL", "rc=%s" % rc2)
        for fn in ("clip_ratio_cells.csv",):
            p = os.path.join(o, fn)
            if os.path.isfile(p):
                shutil.copy(p, os.path.join(out, fn))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return c.finish()


# ---------------------------------------------------------------------------------- CI-04
def cmd_ci04(repo, out):
    c = Check("CI-04", "Layer II (21 trajectories with data; 12 ledger-only)", repo, out)
    exp = load_expected(repo)["layer2"]
    py = sys.executable
    work = tempfile.mkdtemp(prefix="mfdci_")
    try:
        kc = copy_kit(repo, work)
        o = os.path.join(work, "layer2_out")
        os.makedirs(o)
        n = sum(1 for ln in open(os.path.join(kc, "layer2_33traj", "ledgers", "ledger_dt0025.jsonl"), encoding="utf-8") if ln.strip())
        c.add("ledger records (dt 0.0025)", "PASS" if n == exp["ledger_records"] else "FAIL", "records=%d" % n)
        v6 = os.path.join(kc, "layer2_33traj", "06_VERIFY")
        rc, text = c.run("layer2_verify", [py, "-I", "-B", "mfd_independent_verify.py", "--ledger", "../ledgers/ledger_dt0025.jsonl", "--full-dir", "../03_B_FULL", "--tier1-dir", "../04_B_TIER1", "--out", os.path.join(o, "verify_raw.json")], cwd=v6)
        rc_b = None
        if rc == 0:
            rc_b, _ = c.run("layer2_ns15_check", [py, "-I", "-B", "extra_ns15_check.py", "../../layer3_public_kit/evidence_input", "../ledgers", os.path.join(o, "ns15_check.json")], cwd=v6)
        c.tests.append({"suite": "Layer II verification runs", "exit_code": rc if rc != 0 else rc_b, "executed": None})
        if rc != 0 or rc_b != 0:
            c.add("Layer II verification run", "BLOCKED" if (rc is None or rc_b is None) else "FAIL", "verify rc=%s ns15 rc=%s" % (rc, rc_b))
        else:
            rs, ts = c.run("layer2_summary", [py, "tools/layer2_summary.py", os.path.join(o, "verify_raw.json"), os.path.join(o, "ns15_check.json")], cwd=kc)
            fm = re.search(r"B-FULL \(9\): ok (\d+/\d+);\s+B-TIER1 \(10\): classes ok (\d+/\d+);\s+ns15 .*: ok (\d+/\d+)", ts or "")
            cm = re.search(r"class comparisons performed \(4 thresholds each\): (\d+)", ts or "")
            good = rs == 0 and fm and fm.groups() == (exp["b_full"], exp["b_tier1"], exp["ns15"]) and cm and int(cm.group(1)) == exp["class_comparisons"]
            c.add("21 trajectories with data: stored metrics and classes reproduce", "PASS" if good else "FAIL",
                  "B-FULL %s, B-TIER1 %s, ns15 %s, comparisons %s" % (fm and fm.group(1), fm and fm.group(2), fm and fm.group(3), cm and cm.group(1)))
            # asset matrix (uses the stored expected label file; asset inventory only)
            mp = os.path.join(out, "MFD_LayerII_33_Trajectory_Asset_Matrix.csv")
            ra, ta = c.run("layer2_asset_matrix", [py, "tools/build_layer2_asset_matrix.py", kc, os.path.join(kc, "layer3_public_kit", "expected", "label_reconstruction_140.json"), os.path.join(o, "verify_raw.json"), os.path.join(o, "ns15_check.json"), mp], cwd=kc)
            if ra == 0 and os.path.isfile(mp):
                rows = list(csv.DictReader(open(mp, encoding="utf-8-sig")))
                in33 = [r for r in rows if r.get("in_33") == "Y"]
                withd = [r for r in in33 if not (r.get("trajectory_data") or "").startswith("none")]
                ledger_only = len(in33) - len(withd)
                c.add("asset inventory: 33 trajectories, 21 with data, 12 ledger-only", "PASS" if (len(in33), len(withd), ledger_only) == (exp["trajectories"], exp["with_trajectory_data"], exp["ledger_only"]) else "FAIL",
                      "in_33=%d with_data=%d ledger_only=%d" % (len(in33), len(withd), ledger_only))
            else:
                c.add("asset inventory", "BLOCKED" if ra is None else "FAIL", "rc=%s" % ra)
            c.add("12 ledger-only trajectories", "PARTIAL", "ledger summaries only: not re-classified and NOT counted as reproduced from trajectory data; Layer II is therefore at most PARTIAL")
        for fn in ("verify_raw.json", "ns15_check.json"):
            p = os.path.join(o, fn)
            if os.path.isfile(p):
                shutil.copy(p, os.path.join(out, fn))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return c.finish()


# ---------------------------------------------------------------------------------- CI-05
def cmd_ci05(repo, out):
    c = Check("CI-05", "Layer III (stored 140 comparisons)", repo, out)
    exp = load_expected(repo)["layer3"]
    py = sys.executable
    work = tempfile.mkdtemp(prefix="mfdci_")
    try:
        kc = copy_kit(repo, work)
        l3 = os.path.join(kc, "layer3_public_kit")
        tag = "ci"
        rc, text = c.run("layer3_run_all", ["bash", "run_all.sh", py, tag], cwd=l3)
        m = re.search(r"Ran (\d+) tests? in", text or "")
        n = int(m.group(1)) if m else None
        ut = re.search(r"unittest_result=OK", text or "")
        c.tests.append({"suite": "Layer III unit tests", "exit_code": rc, "executed": n})
        if rc is None:
            c.add("Layer III pipeline", "BLOCKED", "could not run")
        else:
            fm = re.search(r"files (\d+) mismatch (\d+)", text or "")
            good = rc == 0 and n == exp["tests"] and ut and fm and int(fm.group(1)) == exp["input_files"] and int(fm.group(2)) == 0 and re.search(r"run_analysis exit=0", text) and re.search(r"INPUT UNCHANGED AFTER RUN", text)
            c.add("Layer III tests, input hashes, analysis run", "PASS" if good else "FAIL", "rc=%s tests=%s (expected %s) input files=%s mismatch=%s" % (rc, n, exp["tests"], fm and fm.group(1), fm and fm.group(2)))
        outdir = os.path.join(l3, "out_" + tag)
        lab = os.path.join(outdir, "label_reconstruction_140.json")
        if os.path.isfile(lab):
            rc2, t2 = c.run("layer3_canonical_check", [py, "-I", "-B", "tools/layer3_canonical_check.py", l3, outdir], cwd=kc)
            rec = re.search(r"records expected/actual (\d+)/(\d+), order identical True", t2 or "")
            good = rc2 == 0 and rec and int(rec.group(1)) == exp["labels"] == int(rec.group(2)) and re.search(r"labels: EQUIVALENT", t2) and re.search(r"report: EQUIVALENT", t2)
            c.add("140 comparison labels: scientifically equivalent to stored result", "PASS" if good else ("BLOCKED" if rc2 is None else "FAIL"), "rc=%s records=%s" % (rc2, rec and rec.groups()))
            stored = open(os.path.join(l3, "expected", "label_reconstruction_140.json.sha256")).read().split()[0]
            ident = sha256_file(lab) == stored
            c.notes.append("raw label file byte-identical to the stored original: %s (informational; scientific equivalence is the criterion)" % ident)
            for fn in ("label_reconstruction_140.json", "analysis_report.json"):
                p = os.path.join(outdir, fn)
                if os.path.isfile(p):
                    shutil.copy(p, os.path.join(out, fn))
        else:
            c.add("140 comparison labels", "BLOCKED", "pipeline produced no label file")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return c.finish()


# ---------------------------------------------------------------------------------- aggregate
CI06 = {"id": "CI-06", "name": "REVTeX independent build", "verdict": "BLOCKED",
        "reason": "Held until the publisher's conditions are confirmed. The Rev.8A build kit contains the manuscript source and is not published. Not run; NOT a pass."}


def overall(results):
    """FAIL > BLOCKED > PARTIAL > PASS. CI-06 is held on purpose: it contributes PARTIAL, not BLOCKED. A missing result is BLOCKED."""
    v = "PASS"
    for r in results:
        s = r["verdict"]
        if r["id"] == "CI-06" and s == "BLOCKED":
            s = "PARTIAL"
        if RANK[s] > RANK[v]:
            v = s
    return v


def cmd_aggregate(inp, out):
    os.makedirs(out, exist_ok=True)
    results, missing = [], []
    for cid in ("CI-01", "CI-02", "CI-03", "CI-04", "CI-05"):
        p = None
        for dp, _, fs in os.walk(inp):
            if "verdict.json" in fs:
                try:
                    d = json.load(open(os.path.join(dp, "verdict.json"), encoding="utf-8"))
                except ValueError:
                    continue
                if d.get("id") == cid:
                    p = d
                    break
        if p is None:
            missing.append(cid)
            results.append({"id": cid, "name": "(no result)", "verdict": "BLOCKED", "reason": "job produced no verdict (did not run or crashed)"})
        else:
            results.append(p)
    results.append(CI06)
    ov = overall(results)
    summary = {"overall": ov, "commit": commit_id("."), "utc": utc(), "results": [{"id": r["id"], "name": r["name"], "verdict": r["verdict"]} for r in results],
               "missing": missing, "tests": [t for r in results for t in r.get("tests", [])]}
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)
    L = ["# MFD verification summary", "", "- target commit: `%s`" % summary["commit"], "- finished (UTC): %s" % summary["utc"], "- **overall: %s**" % ov, "",
         "| ID | check | verdict |", "|---|---|---|"]
    for r in results:
        L.append("| %s | %s | %s |" % (r["id"], r["name"], r["verdict"]))
    L += ["", "## Tests executed", "", "| suite | exit code | executed |", "|---|---|---|"]
    for t in summary["tests"]:
        L.append("| %s | %s | %s |" % (t["suite"], t["exit_code"], t["executed"]))
    L += ["", "## Notes", "- PASS only means the stated check passed. PARTIAL (CI-04): 12 of the 33 Layer II trajectories are ledger-only and are not claimed as reproduced from data.",
          "- CI-06 is held (BLOCKED, not run) until the publisher's conditions are confirmed; it is not counted as a pass.",
          "- A scientific or build verdict beyond these checks is out of scope. These runs re-verify stored public assets; they are producer-side automation, not a third-party replication."]
    open(os.path.join(out, "SUMMARY.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    lines = []
    for dp, _, fs in os.walk(inp):
        for fn in fs:
            p = os.path.join(dp, fn)
            lines.append("%s  %s" % (sha256_file(p), os.path.relpath(p, inp).replace(os.sep, "/")))
    open(os.path.join(out, "EVIDENCE_SHA256SUMS.txt"), "w", encoding="utf-8").write("\n".join(sorted(lines, key=lambda s: s.split("  ", 1)[1])) + "\n")
    print(open(os.path.join(out, "SUMMARY.md"), encoding="utf-8").read())
    return {"PASS": 0, "PARTIAL": 0, "BLOCKED": 3, "FAIL": 1}[ov]


def main(argv):
    if len(argv) != 4 or argv[1] not in ("env", "ci01", "ci02", "ci03", "ci04", "ci05", "aggregate"):
        print(__doc__)
        return 2
    cmd, a, b = argv[1], os.path.abspath(argv[2]), os.path.abspath(argv[3])
    if cmd == "aggregate":
        return cmd_aggregate(a, b)
    return {"env": cmd_env, "ci01": cmd_ci01, "ci02": cmd_ci02, "ci03": cmd_ci03, "ci04": cmd_ci04, "ci05": cmd_ci05}[cmd](a, b)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
