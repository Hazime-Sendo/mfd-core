#!/usr/bin/env python3
"""Limited strict-mode diagnostic (at most 5 subprocess runs). Separates (a) the unittest result from (b) the exit status of the WHOLE process.
Does not change any test, tolerance or exit code; a non-zero process exit is reported as such (never rewritten to success).
Runs (each in its own subprocess; stdout/stderr captured):
  1 default mode            : unittest discover (36 tests)
  2 strict mode             : -X dev -W error -X faulthandler  unittest discover
  3 strict, import only     : -X dev -W error -X faulthandler  -c "import numpy"            (native extension load/unload, no test code)
  4 strict, import scipy    : -X dev -W error -X faulthandler  -c "import numpy, scipy"     (skipped silently if scipy is absent)
  5 strict, bare interpreter: -X dev -W error -X faulthandler  -c "pass"                    (interpreter start/stop only)
Usage: python3 -I -B tools/strict_mode_diagnostic.py [out.json]   (run from the kit root or any directory)
Interpretation (hypotheses, NOT conclusions): if 2 fails but 3/4/5 pass, the fault depends on the test body; if 3 fails, a native extension at
interpreter shutdown; if 5 fails, the interpreter build/OS. If nothing fails the anomaly is NOT reproduced in this environment (cause unidentified).
On Windows a negative/large exit status such as -1073741819 (0xC0000005) is an NTSTATUS access-violation code."""
import os, sys, subprocess, platform, json, re, datetime
KIT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TESTS = os.path.join(KIT, "layer3_public_kit", "code", "tests")
STRICT = ["-X", "dev", "-W", "error", "-X", "faulthandler"]
def ntstatus(rc):
    u = rc & 0xFFFFFFFF
    names = {0xC0000005: "STATUS_ACCESS_VIOLATION", 0xC0000409: "STATUS_STACK_BUFFER_OVERRUN", 0xC0000374: "STATUS_HEAP_CORRUPTION", 0xC000013A: "STATUS_CONTROL_C_EXIT"}
    return "0x%08X %s" % (u, names.get(u, "")) if rc < 0 or rc > 255 else ""
def run(name, args, cwd=None, env_extra=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", EVIDENCE_DIR=os.path.join(KIT, "layer3_public_kit", "evidence_input"))
    if env_extra: env.update(env_extra)
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True, cwd=cwd or KIT, env=env, errors="replace")
    err = p.stderr
    m = re.search(r"^Ran (\d+) tests? in", err, re.M)
    r = dict(run=name, args=" ".join(args), process_exit=p.returncode, ntstatus=ntstatus(p.returncode), tests_ran=int(m.group(1)) if m else None,
             tests_ok=bool(re.search(r"^OK\s*$", err, re.M)), stderr_lines=len(err.splitlines()), stderr_tail=err.splitlines()[-12:])
    r["test_body_vs_process"] = ("tests OK, process exit %d" % p.returncode) if r["tests_ok"] else ("no test result line; process exit %d" % p.returncode)
    print("[%s] exit=%s tests_ran=%s tests_ok=%s %s" % (name, p.returncode, r["tests_ran"], r["tests_ok"], r["ntstatus"]))
    return r
def main(out):
    info = dict(date=datetime.datetime.now().astimezone().isoformat(timespec="seconds"), python=sys.version, executable_name=os.path.basename(sys.executable), platform=platform.platform(),
                machine=platform.machine())
    for m in ("numpy", "scipy"):
        try: mod = __import__(m); info[m] = mod.__version__
        except Exception as e: info[m] = "not importable (%s)" % type(e).__name__
    runs = [run("1_default_tests", ["-I", "-B", "-m", "unittest", "discover", "-s", TESTS]),
            run("2_strict_tests", STRICT + ["-I", "-B", "-m", "unittest", "discover", "-s", TESTS]),
            run("3_strict_import_numpy", STRICT + ["-I", "-B", "-c", "import numpy"]),
            run("4_strict_import_numpy_scipy", STRICT + ["-I", "-B", "-c", "import numpy, scipy"]) if info["scipy"][0].isdigit() else dict(run="4_strict_import_numpy_scipy", skipped="scipy not installed"),
            run("5_strict_bare_interpreter", STRICT + ["-I", "-B", "-c", "pass"])]
    bad = [r["run"] for r in runs if r.get("process_exit") not in (0, None)]
    verdict = ("ANOMALY OBSERVED in: " + ", ".join(bad) + " (cause not determined by this script)") if bad else "anomaly NOT reproduced in this environment (cause unidentified)"
    print(verdict)
    json.dump(dict(environment=info, runs=runs, verdict=verdict), open(out, "w"), indent=1)
    return 0   # diagnostic only: its own status never hides or converts a run's exit status (recorded per run)
if __name__ == "__main__": sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "strict_mode_diagnostic.json"))
