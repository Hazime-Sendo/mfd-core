"""Per-trajectory asset matrix for the 35 classified trajectories (33 at dt=0.0025 + 2 at dt=0.00125). Read-only.
usage: build_layer2_asset_matrix.py <kit_root> <label_reconstruction_140.json> <layer2_raw.json> <ns15.json> <out.csv>"""
import sys, os, json, csv, hashlib
root, lab, raw, n15, out = sys.argv[1:6]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest() if os.path.exists(p) else ''
L = os.path.join(root, 'layer2_33traj'); EV = os.path.join(root, 'layer3_public_kit', 'evidence_input')
led = {}; lsha = {}
for f in ('ledger_dt0025.jsonl', 'ledger_dt00125.jsonl'):
    p = os.path.join(L, 'ledgers', f); lsha[f] = sha(p)
    for line in open(p, encoding='utf-8'):
        r = json.loads(line); led[r['key']] = (f, hashlib.sha256(line.rstrip('\n').encode()).hexdigest(), r)
labs = {}
for x in json.load(open(lab)): labs.setdefault(x['key'], []).append(x)
ver = {}
for r in json.load(open(raw))['results'] + json.load(open(n15)): ver.setdefault(r['key'], []).append(r)
rows = []
for k, (f, rsha, r) in led.items():
    s = r['spec']; dt = s['DT']
    m2 = [p for p in (os.path.join(L, '03_B_FULL', k + '.m2'), os.path.join(EV, k + '.m2')) if os.path.exists(p)]
    nz = [p for p in (os.path.join(L, '04_B_TIER1', k + '.npz'), os.path.join(EV, k + '.npz')) if os.path.exists(p)]
    m2 = m2[0] if m2 else ''; nz = nz[0] if nz else ''
    vs = ver.get(k, []); vok = bool(vs) and all(not v.get('error') and all((v.get('classes_match') or {0: False}).values()) for v in vs)
    lb = labs.get(k, []); partial = sum(1 for x in lb if x['compare'] == 'PARTIAL'); match = sum(1 for x in lb if x['compare'] == 'MATCH')
    has_term = bool(m2 or nz)
    rows.append(dict(trajectory=k, dt=dt, in_33=('Y' if dt == 0.0025 else 'N (dt=0.00125 pair)'), a=s['a'], native_seed=s['ns'],
        ledger_file=f, ledger_file_sha256=lsha[f], ledger_record_sha256=rsha, ledger_state=r['summary']['state'],
        ledger_classes_by_theta=' / '.join(r['classes'][t] for t in ('0.01', '0.03', '0.1', '0.3')),
        m2_file=os.path.relpath(m2, root) if m2 else '', m2_sha256=sha(m2) if m2 else '',
        npz_file=os.path.relpath(nz, root) if nz else '', npz_sha256=sha(nz) if nz else '',
        trajectory_data=(('M2 full + NPZ tier-1' if nz else 'M2 full') if m2 else ('NPZ tier-1' if nz else 'none (ledger summary only)')),
        true_terminal_coordinates=('YES (x_final stored)' if has_term else 'NO'),
        reclassification=('YES: native/mirror/other recomputed from true terminal coordinates with frozen kabsch' if has_term else 'LIMITED: branch-independent classes only (stagnation/unconverged/anomaly) from ledger; native/mirror not reconstructible'),
        module_verification=('4/4 classes match, file/content hash match where applicable' if vok else ('not run (no trajectory data)' if not vs else 'CHECK')),
        labels_MATCH=match, labels_PARTIAL=partial,
        public_eligibility='Scientific data only; no authorization/personal fields found by scan. Publication of Layer II containers needs the research lead\'s approval (policy item 7).',
        missing_assets=('' if has_term else 'M2/NPZ trajectory containers; terminal coordinates'),
        note=('B-REGEN recipe + existing terminal log available' if '04_B_TIER1' in nz else '')))
rows.sort(key=lambda x: (x['dt'] != 0.0025, x['native_seed'], x['a']))
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print('rows', len(rows), 'with trajectory data', sum(1 for r in rows if r['trajectory_data'] != 'none (ledger summary only)'), 'in_33 with data', sum(1 for r in rows if r['in_33'] == 'Y' and r['trajectory_data'] != 'none (ledger summary only)'))
