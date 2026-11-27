"""Added in Rev.2 (not part of the original extracted module): applies the module's own verify_full / verify_tier1 to the four ns15 trajectories
(a=8,16 at dt=0.0025 and 0.00125) whose containers are shipped in layer3_public_kit/evidence_input. Reads only; no simulation.
usage: python -I extra_ns15_check.py <evidence_input_dir> <ledgers_dir> <out.json>"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mfd_independent_verify as M
ev, ld, out = sys.argv[1:4]; res = []
for dt, lf in (('0.0025', 'ledger_dt0025.jsonl'), ('0.00125', 'ledger_dt00125.jsonl')):
    led = M.load_ledger(os.path.join(ld, lf))
    for a in ('8', '16'):
        k = f'ns15_a{a}_D500_dt{dt}_s0'
        res.append(M.verify_full(k, os.path.join(ev, k + '.m2'), led))
        res.append(M.verify_tier1(k, os.path.join(ev, k + '.npz'), led))
json.dump(res, open(out, 'w'), default=M._jd, indent=1, ensure_ascii=False); print('written', out)
