# 入力証拠のハッシュ照合。python tools/verify_inputs.py  (evidence_input/ と expected_evidence_sha256.txt を比較)
import hashlib, os, sys
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
exp={}
for l in open(os.path.join(root,"expected_evidence_sha256.txt"),encoding="utf-8"):
    if l.strip(): h,n=l.split(None,1); exp[n.strip()]=h
bad=0
for n,h in sorted(exp.items()):
    p=os.path.join(root,"evidence_input",n)
    got=hashlib.sha256(open(p,"rb").read()).hexdigest() if os.path.exists(p) else None
    if got!=h: bad+=1; print("MISMATCH",n,got)
extra=set(os.listdir(os.path.join(root,"evidence_input")))-set(exp)
print("files",len(exp),"mismatch",bad,"extra",sorted(extra)); sys.exit(1 if bad or extra else 0)
