#!/usr/bin/env python3
"""Mechanical integrity check of the public kit (Rev.4).   Usage:
    python3 -I -B tools/verify_kit_manifest.py [KIT_ROOT] [--zip FILE.zip] [--json OUT.json] [--allowlist-sha SHA256]
Every registered or present file gets exactly ONE state; nothing is PASS unless its content was read and hashed on an ordinary file:
  OK              regular file, readable, SHA-256 equals the manifest
  MISMATCH        regular file, readable, SHA-256 differs
  NOT_FOUND       the path does not exist (lstat: file not found)
  UNREADABLE      the path exists but opening/reading failed (permission, I/O error, offline data)
  SPECIAL_STATE   not an ordinary file: symbolic link, non-regular node, Windows reparse point / cloud placeholder / offline or recall-on-access
                  attribute. NEVER counted as PASS, even when the bytes can be read; re-run on an ordinary local file system.
  PATH_RESOLUTION the path could not be resolved as written (too long, invalid name, found only through the Windows long-path prefix)
Other findings: unregistered files, files/entries not in the public allow-list, unclassified file types, duplicate and unsafe paths,
ZIP CRC errors. The public allow-list (tools/public_allowlist.txt) is the closed set of files released for publication; its SHA-256 may be
checked against an externally supplied value (--allowlist-sha). No manifest lists itself (no circular reference).
Exit codes: 0 all clear / 1 integrity problem (mismatch, missing, unregistered, not in allow-list, CRC, duplicate, unsafe, format) /
            2 environment state prevented verification (UNREADABLE, SPECIAL_STATE, PATH_RESOLUTION) and nothing else failed.
Scopes: top KIT_MANIFEST_sha256.txt (whole kit except the runs/ output area and itself) and the lower-level manifests it lists.
"""
import os, sys, hashlib, re, stat, zipfile, json
TOP = "KIT_MANIFEST_sha256.txt"
ALLOWLIST = "tools/public_allowlist.txt"
OUTPUT_AREAS = ("runs",)
SUB = [("layer1_300trial", "layer1_300trial/SHA256SUMS_layer1.txt"), ("layer2_33traj", "layer2_33traj/SHA256SUMS_layer2.txt"),
       ("layer3_public_kit", "layer3_public_kit/KIT_MANIFEST_sha256.txt"), ("layer3_public_kit/evidence_input", "layer3_public_kit/evidence_input/SHA256SUMS.txt")]
# generic file classes (by extension) allowed in a public kit; anything else is 'unclassified'
CLASSES = {"documentation": (".md", ".txt", ".log"), "code": (".py", ".sh", ".ipynb"), "data": (".json", ".jsonl", ".csv", ".m2", ".npz", ".sha256"),
           "integrity-list": (".sha256",)}
ALLOWED_EXT = {e for v in CLASSES.values() for e in v}
FA = {"REPARSE": 0x400, "RECALL_ON_DATA_ACCESS": 0x400000, "RECALL_ON_OPEN": 0x40000, "OFFLINE": 0x1000}
SAFE_NAME = re.compile(r"^[A-Za-z0-9._\-+@=,() /]+$")   # public names are ASCII only (portable across Windows, PowerShell, zip tools)

def native(p):
    """On Windows use the extended-length prefix so that long paths are not mistaken for missing files."""
    p = os.path.abspath(p)
    if os.name == "nt" and not p.startswith("\\\\?\\"):
        p = "\\\\?\\UNC\\" + p[2:] if p.startswith("\\\\") else "\\\\?\\" + p
    return p

def inspect(path):
    """-> (state, detail). Does not hash."""
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        if os.name == "nt":
            try:
                os.lstat(native(path)); return "PATH_RESOLUTION", "found only through the extended-length (long path) prefix"
            except OSError: pass
        return "NOT_FOUND", ""
    except OSError as e:
        return "PATH_RESOLUTION", "%s: %s" % (type(e).__name__, e.strerror or e)
    if stat.S_ISLNK(st.st_mode): return "SPECIAL_STATE", "symbolic link"
    if not stat.S_ISREG(st.st_mode): return "SPECIAL_STATE", "non-regular file type"
    attrs = getattr(st, "st_file_attributes", 0)
    flags = [k for k, v in FA.items() if attrs & v]
    if flags or getattr(st, "st_reparse_tag", 0): return "SPECIAL_STATE", "attributes " + ",".join(flags or ["reparse"])
    return "REGULAR", ""

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def unsafe(p): return p.startswith("/") or p.startswith("\\") or "\\" in p or ".." in p.split("/") or re.match(r"^[A-Za-z]:", p) is not None

class Report:
    KEYS = ["ok", "mismatch", "not_found", "unreadable", "special_state", "path_resolution", "unregistered", "not_in_allowlist",
            "unclassified", "crc_errors", "duplicate_paths", "unsafe_paths", "format_errors"]
    def __init__(s): s.c = dict.fromkeys(s.KEYS, 0); s.items = []
    def add(s, key, name, detail=""):
        s.c[key] += 1
        if key != "ok": s.items.append((key.upper(), name, detail)); print(key.upper(), name, detail)

def check_file(rep, root, rel, want):
    p = os.path.join(root, rel)
    state, d = inspect(p)
    if state == "NOT_FOUND": rep.add("not_found", rel); return
    if state == "PATH_RESOLUTION": rep.add("path_resolution", rel, d); return
    if state == "SPECIAL_STATE":
        rep.add("special_state", rel, d + " (not accepted as PASS)"); return
    try:
        h = sha(p)
    except OSError as e:
        rep.add("unreadable", rel, "%s: %s" % (type(e).__name__, e.strerror or e)); return
    if h != want: rep.add("mismatch", rel)
    else: rep.add("ok", rel)

def parse(rep, path):
    ent, seen = [], set()
    with open(path, encoding="utf-8") as f:
        for i, l in enumerate(f, 1):
            l = l.rstrip("\n")
            if not l.strip(): continue
            m = re.match(r"^([0-9a-f]{64})  (.+)$", l)
            if not m: rep.add("format_errors", os.path.basename(path), "line %d" % i); continue
            h, n = m.groups()
            if n in seen: rep.add("duplicate_paths", n)
            seen.add(n)
            if unsafe(n): rep.add("unsafe_paths", n)
            ent.append((h, n))
    return ent

def walk_files(base, skip_top=()):
    for dp, dn, fn in os.walk(base):
        dn[:] = sorted(d for d in dn if os.path.relpath(os.path.join(dp, d), base).replace(os.sep, "/") not in skip_top)
        for n in sorted(fn): yield os.path.relpath(os.path.join(dp, n), base).replace(os.sep, "/")

def load_allowlist(rep, root):
    p = os.path.join(root, ALLOWLIST)
    if not os.path.isfile(p): rep.add("not_found", ALLOWLIST, "public allow-list missing"); return None
    with open(p, encoding="utf-8") as f: return set(l.rstrip("\n") for l in f if l.strip())

def check_scope(rep, root, base, mpath, allow, skip_top=()):
    ent = parse(rep, mpath); reg = set()
    prefix = os.path.relpath(base, root).replace(os.sep, "/"); prefix = "" if prefix == "." else prefix + "/"
    for h, n in ent:
        reg.add(n)
        if unsafe(n): continue
        if allow is not None and (prefix + n) not in allow: rep.add("not_in_allowlist", prefix + n)
        check_file(rep, base, n, h)
    own = os.path.relpath(mpath, base).replace(os.sep, "/")
    for rel in walk_files(base, skip_top):
        if rel != own and rel not in reg: rep.add("unregistered", prefix + rel)
    return len(ent)

def main(a):
    root = os.path.abspath(a[1]) if len(a) > 1 and not a[1].startswith("--") else os.getcwd()
    arg = lambda k: a[a.index(k) + 1] if k in a else None
    zpath, jpath, want_allow = arg("--zip"), arg("--json"), arg("--allowlist-sha")
    rep = Report()
    allow = load_allowlist(rep, root)
    if want_allow and allow is not None:
        if sha(os.path.join(root, ALLOWLIST)) != want_allow: rep.add("mismatch", ALLOWLIST, "allow-list SHA-256 differs from the externally supplied value")
    # classification and allow-list coverage of everything physically present (outside runs/)
    for rel in walk_files(root, OUTPUT_AREAS):
        ext = os.path.splitext(rel)[1].lower()
        if ext not in ALLOWED_EXT: rep.add("unclassified", rel, "extension %r is not in a public file class" % ext)
        if not SAFE_NAME.match(rel): rep.add("unsafe_paths", rel, "characters outside the ASCII public name set")
        if allow is not None and rel not in allow and rel not in (TOP,): rep.add("not_in_allowlist", rel)
    n = check_scope(rep, root, root, os.path.join(root, TOP), allow, skip_top=OUTPUT_AREAS)
    print("top manifest entries:", n)
    for d, m in SUB:
        base, mp = os.path.join(root, d), os.path.join(root, m)
        if not os.path.isfile(mp): rep.add("not_found", m, "sub-manifest"); continue
        k = check_scope(rep, root, base, mp, None)
        print("sub-manifest", m, "entries:", k)
    zn = None
    if zpath:
        with zipfile.ZipFile(zpath) as z:
            bad = z.testzip()
            if bad is not None: rep.add("crc_errors", bad)
            names = [i.filename for i in z.infolist()]; zn = len(names)
            if len(names) != len(set(names)): rep.add("duplicate_paths", "zip", "%d duplicate entries" % (len(names) - len(set(names))))
            for nme in names:
                if unsafe(nme.rstrip("/")): rep.add("unsafe_paths", nme, "zip entry")
        print("zip entries:", zn)
    for k in Report.KEYS: print("%-16s %d" % (k, rep.c[k]))
    integrity = sum(rep.c[k] for k in Report.KEYS if k not in ("ok", "unreadable", "special_state", "path_resolution"))
    env = rep.c["unreadable"] + rep.c["special_state"] + rep.c["path_resolution"]
    verdict = "KIT INTEGRITY: OK" if not integrity and not env else ("KIT INTEGRITY: PROBLEMS FOUND" if integrity else "KIT INTEGRITY: NOT VERIFIED (environment/file state; re-run on an ordinary local file system)")
    print(verdict)
    if jpath:
        with open(jpath, "w", encoding="utf-8") as f: json.dump({"counts": rep.c, "findings": rep.items, "verdict": verdict, "zip_entries": zn}, f, indent=1)
    return 1 if integrity else (2 if env else 0)

if __name__ == "__main__": sys.exit(main(sys.argv))
