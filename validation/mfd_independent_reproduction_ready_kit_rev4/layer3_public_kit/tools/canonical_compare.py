"""Canonical (structured) comparison of Layer III outputs.   Rev.3 of the kit.

Two different checks are kept apart on purpose:
  A. ORIGINAL INTEGRITY: SHA-256 of stored original files, byte for byte (tools/verify_inputs.py, tools/verify_kit_manifest.py).
  B. SCIENTIFIC EQUIVALENCE of a re-computed output (this module): JSON is parsed, normalised and compared as data.
     A canonical hash is NOT the hash of the file; never use one in place of the other.

Normalisation (see NORMALIZATION_SPEC.md):
  * input is UTF-8; a leading BOM is stripped; CR LF / CR are equivalent to LF (irrelevant to a JSON parse);
  * duplicate object keys, NaN, +Infinity, -Infinity are REJECTED (the file is invalid, not "equal");
  * object key order is irrelevant (canonical form sorts keys); array order is kept unless stated (label records
    are matched by key (key, theta); order difference is reported, not failed);
  * canonical bytes = json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) in UTF-8, no trailing newline;
  * numbers: int stays int, float uses Python repr; bool is not a number; missing value (null) is a value and must match;
  * label / identifier fields must match exactly; numeric fields: exact for labels file; relative tolerance 1e-9 for the
    report file (the criterion already used by tools/compare_runs.py; not widened).
"""
import json, hashlib, sys, math

LABEL_REQUIRED = {"key": str, "theta": (int, float), "E": str, "y_rebuilt": str, "y_ledger": str, "compare": str,
                  "cross_consistent": bool, "source": str, "note": str, "ledger_state": str, "chir": str, "anomaly": bool,
                  "anomaly_source": str}
LABEL_NULLABLE = ("y_rebuilt", "chir")   # null = "not reconstructible" (the 71 PARTIAL records); null is a value and must match
EXPECTED_RECORDS = 140
REPORT_RTOL = 1e-9
REPORT_IGNORE_TOP = ("environment",)

class InvalidJSON(ValueError):
    pass

def _no_const(name):
    raise InvalidJSON("non-finite value %s" % name)

def _pairs(pairs):
    d = {}
    for k, v in pairs:
        if k in d: raise InvalidJSON("duplicate key %r" % k)
        d[k] = v
    return d

def loads_strict(data):
    if isinstance(data, bytes):
        if data.startswith(b"\xef\xbb\xbf"): data = data[3:]
        data = data.decode("utf-8")
    return json.loads(data, object_pairs_hook=_pairs, parse_constant=_no_const)

def load_strict(path):
    with open(path, "rb") as f: return loads_strict(f.read())

def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def canonical_sha256(obj):
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()

def _isnum(x): return isinstance(x, (int, float)) and not isinstance(x, bool)

def compare_labels(expected, actual, n_expected=EXPECTED_RECORDS):
    """Return (problems, info). problems empty <=> scientifically equivalent."""
    P, info = [], {}
    for name, arr in (("expected", expected), ("actual", actual)):
        if not isinstance(arr, list): P.append("%s is not a list" % name); return P, info
    def index(arr, name):
        idx, seen = {}, set()
        for i, r in enumerate(arr):
            if not isinstance(r, dict): P.append("%s[%d] is not an object" % (name, i)); continue
            for f, t in LABEL_REQUIRED.items():
                if f not in r: P.append("%s[%d] missing required field %s" % (name, i, f)); continue
                v = r[f]
                if v is None and f in LABEL_NULLABLE: continue
                if t is bool:
                    if not isinstance(v, bool): P.append("%s[%d].%s wrong type" % (name, i, f))
                elif t == (int, float):
                    if not _isnum(v): P.append("%s[%d].%s wrong type" % (name, i, f))
                elif not isinstance(v, t) or isinstance(v, bool): P.append("%s[%d].%s wrong type" % (name, i, f))
            k = (r.get("key"), r.get("theta"))
            if k in seen: P.append("%s duplicate record %r" % (name, k))
            seen.add(k); idx[k] = r
        return idx
    ie, ia = index(expected, "expected"), index(actual, "actual")
    info["n_expected"], info["n_actual"] = len(expected), len(actual)
    if len(actual) != n_expected: P.append("actual has %d records, expected %d" % (len(actual), n_expected))
    for k in sorted(set(ie) - set(ia), key=repr): P.append("record missing in actual: %r" % (k,))
    for k in sorted(set(ia) - set(ie), key=repr): P.append("unexpected record in actual: %r" % (k,))
    for k in sorted(set(ie) & set(ia), key=repr):
        a, e = ia[k], ie[k]
        for f in sorted(set(a) | set(e)):
            if f not in a or f not in e: P.append("%r field set differs at %s" % (k, f)); continue
            if a[f] != e[f] or type(a[f]) is not type(e[f]) and not (_isnum(a[f]) and _isnum(e[f])):
                P.append("%r field %s: expected %r actual %r" % (k, f, e[f], a[f]))
    info["order_identical"] = [(r.get("key"), r.get("theta")) for r in expected] == [(r.get("key"), r.get("theta")) for r in actual]
    return P, info

def compare_report(expected, actual, rtol=REPORT_RTOL, ignore_top=REPORT_IGNORE_TOP):
    P = []
    def walk(x, y, p):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in sorted(set(x) | set(y)):
                if p == "" and k in ignore_top: continue
                if k not in x or k not in y: P.append("%s/%s present in only one side" % (p, k)); continue
                walk(x[k], y[k], p + "/" + k)
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y): P.append("%s length %d vs %d" % (p, len(x), len(y))); return
            for i, (u, v) in enumerate(zip(x, y)): walk(u, v, "%s[%d]" % (p, i))
        elif _isnum(x) and _isnum(y):
            if x != y and abs(x - y) > rtol * max(abs(x), abs(y), 1e-300): P.append("%s numeric %r vs %r (> rtol %g)" % (p, x, y, rtol))
        elif type(x) is not type(y) or x != y: P.append("%s %r vs %r" % (p, x, y))
    walk(expected, actual, "")
    return P

def main(argv):
    if len(argv) < 2 or argv[1] not in ("labels", "report", "canon-hash"):
        print("usage: canonical_compare.py labels EXPECTED.json ACTUAL.json | report EXPECTED.json ACTUAL.json | canon-hash FILE.json"); return 2
    try:
        if argv[1] == "canon-hash":
            o = load_strict(argv[2]); print(canonical_sha256(o), "(canonical hash; not the file hash)"); return 0
        e, a = load_strict(argv[2]), load_strict(argv[3])
    except (InvalidJSON, ValueError, OSError) as ex:
        print("INVALID INPUT:", ex); return 3
    if argv[1] == "labels":
        P, info = compare_labels(e, a)
        print("records expected/actual:", info.get("n_expected"), info.get("n_actual"), "| order identical:", info.get("order_identical"))
        print("canonical sha256 expected:", canonical_sha256(e)); print("canonical sha256 actual:  ", canonical_sha256(a))
    else:
        P = compare_report(e, a)
    for p in P[:50]: print("DIFF", p)
    print("EQUIVALENT" if not P else "NOT EQUIVALENT (%d differences)" % len(P))
    return 0 if not P else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))
