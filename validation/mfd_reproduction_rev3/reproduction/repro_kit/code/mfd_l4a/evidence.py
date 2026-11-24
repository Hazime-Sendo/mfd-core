"""A1 Evidence Loader: read-only. Distinguishes MISSING / HASH_MISMATCH / OK / UNLISTED. Never opens a file for writing."""
import hashlib, json, os
from dataclasses import dataclass, asdict

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:            # read-only binary
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

@dataclass
class FileRecord:
    name: str; size: int; sha256: str; listed_sha256: str; integrity: str; load: str = "NOT_LOADED"

class EvidenceError(Exception): pass

class Evidence:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        if not os.path.isdir(self.root): raise EvidenceError("evidence root missing: %s" % root)
        self.records = {}
        self._scan()
    def _sums(self):
        p = os.path.join(self.root, "SHA256SUMS.txt")
        if not os.path.isfile(p): raise EvidenceError("SHA256SUMS.txt missing (integrity reference absent)")
        d = {}
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    h, n = line.split(None, 1); d[n.strip().lstrip("*")] = h
        return d
    def _scan(self):
        sums = self._sums()
        names = sorted(n for n in os.listdir(self.root) if os.path.isfile(os.path.join(self.root, n)))
        for n in sorted(set(names) | set(sums)):
            p = os.path.join(self.root, n)
            if n not in names:
                self.records[n] = FileRecord(n, 0, "", sums[n], "MISSING"); continue
            h = sha256_file(p)
            if n == "SHA256SUMS.txt": st = "REFERENCE_FILE"
            elif n not in sums: st = "UNLISTED"
            else: st = "OK" if sums[n] == h else "HASH_MISMATCH"
            self.records[n] = FileRecord(n, os.path.getsize(p), h, sums.get(n, ""), st)
    def path(self, n): return os.path.join(self.root, n)
    def load_json(self, n):
        r = self.records.get(n)
        if r is None or r.integrity == "MISSING": raise EvidenceError("missing: " + n)
        if r.integrity == "HASH_MISMATCH": raise EvidenceError("hash mismatch (stop condition): " + n)
        with open(self.path(n), encoding="utf-8") as f: obj = json.load(f)
        r.load = "LOADED"; return obj
    def load_jsonl(self, n):
        r = self.records.get(n)
        if r is None or r.integrity == "MISSING": raise EvidenceError("missing: " + n)
        if r.integrity == "HASH_MISMATCH": raise EvidenceError("hash mismatch (stop condition): " + n)
        with open(self.path(n), encoding="utf-8") as f: rows = [json.loads(l) for l in f if l.strip()]
        r.load = "LOADED"; return rows
    def load_npz(self, n):
        import numpy as np
        r = self.records.get(n)
        if r is None or r.integrity == "MISSING": raise EvidenceError("missing: " + n)
        if r.integrity == "HASH_MISMATCH": raise EvidenceError("hash mismatch (stop condition): " + n)
        z = np.load(self.path(n), allow_pickle=False); out = {k: z[k] for k in z.files}; r.load = "LOADED"; return out
    def summary(self): return [asdict(r) for r in self.records.values()]
