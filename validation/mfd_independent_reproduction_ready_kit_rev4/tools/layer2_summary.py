"""Summarise layer-II raw verification results (no verdict beyond counts). usage: layer2_summary.py verify_raw.json ns15.json"""
import sys, json
a = json.load(open(sys.argv[1]))['results']; b = json.load(open(sys.argv[2]))
def ok(r):
    cm = r.get('classes_match') or {}
    return not r.get('error') and len(cm) == 4 and all(cm.values()) and r.get('file_sha256_match') in (True, None) and r.get('content_hash_match') in (True, None) and r.get('indices_match') in (True, None)
full = [r for r in a if r['route'] == 'B-FULL']; t1 = [r for r in a if r['route'] == 'B-TIER1']
fb = [r for r in b if r.get('route') == 'B-FULL' or r.get('file_sha256_match') is True]
print(f"B-FULL (9): ok {sum(ok(r) for r in full)}/9;  B-TIER1 (10): classes ok {sum(ok(r) for r in t1)}/10;  ns15 four trajectories x (full, tier1): ok {sum(ok(r) for r in b)}/{len(b)}")
n = sum(len(r['classes_match']) for r in a if r.get('classes_match')) + sum(len(r['classes_match']) for r in b if r.get('classes_match'))
print("class comparisons performed (4 thresholds each):", n)
sys.exit(0 if all(ok(r) for r in a + b) else 1)
