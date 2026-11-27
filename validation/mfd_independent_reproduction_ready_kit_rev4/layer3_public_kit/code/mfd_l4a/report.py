"""A6 Report Writer. Evidence state, analysis feasibility and result are separate fields (no single rank)."""
import json, platform, hashlib, os, sys
import numpy as np
STATUSES = ("VERIFIED", "REVIEW", "NOT VERIFIED", "NOT ESTIMABLE")

def code_version(pkg_dir):
    h = hashlib.sha256()
    for n in sorted(os.listdir(pkg_dir)):
        if n.endswith(".py"):
            h.update(n.encode())
            with open(os.path.join(pkg_dir, n), "rb") as f: h.update(f.read())
    return h.hexdigest()

def item(name, evidence_state, feasibility, result, detail=None):
    assert evidence_state in STATUSES and feasibility in ("ESTIMABLE", "PARTIAL", "NOT ESTIMABLE") and result in STATUSES + ("MATCH", "MISMATCH", "DESCRIPTIVE")
    return {"item": name, "evidence_state": evidence_state, "analysis_feasibility": feasibility, "result": result, "detail": detail}

def env_info(pkg_dir):
    return {"python": sys.version.split()[0], "numpy": np.__version__, "platform": platform.platform(), "analysis_code_sha256": code_version(pkg_dir)}

def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=1, default=str)
