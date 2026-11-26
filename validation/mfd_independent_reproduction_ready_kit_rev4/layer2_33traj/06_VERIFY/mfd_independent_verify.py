# -*- coding: utf-8 -*-
"""MFD 独立照合モジュール(第9号案 ④-B)。
- 凍結コントローラー rbsh6/mfd_rbsh_v2_controller.py(SHA-256 12bccc7f870412b46f97b33b9c2f26da34a9ab36a9cc367ba8a094ab3152ba5d)から
  指定の関数・定数を行単位で機械抽出した。抽出ブロックは「=== EXTRACTED」から「=== END EXTRACTED」の間で、原典と同一テキスト(extraction_lineage.json に原典行番号・ハッシュを記録)。
- 変更は import の解決のみ(godel_original・提案写像機構への依存なし)。数理式・閾値・配列順序・ハッシュ方式・分類規則は不変。
- 研究・新規実験を行わない。照合のみ。第三者環境で実行されるまで結果は存在しない。
"""
import os, sys, io, json, lzma, hashlib, struct, importlib.util, platform
import numpy as np
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = os.environ.get('MFD_FROZEN_DIR', os.path.join(HERE, '..', '02_FROZEN_CODE'))
EXPECTED_FROZEN = {'scripts/51_main_run_v3.py': '8c4a838a80e133bed7b1757f1bbf038391c460025d5089f5fd4b8f1541ce6cf5', 'scripts/52_indices_v3.py': '544c451aac99a2ba2b27fc27226e47a1f1b6b715daf23d65714534faa120d3ae',
                   'src/mfd_discrete_gradient.py': 'b3dc37b1e0145f65c1be7dea66b933cd4fe7c41eafc2cf75827611900c9353c3', 'src/metriplectic_folding.py': '5aaadb299400482fa07d524c6061a2b222f5d39be677a826dddc84d204e9636d'}
def _frozen_ok():
    bad = {k: hashlib.sha256(open(os.path.join(FROZEN, k), 'rb').read()).hexdigest() for k in EXPECTED_FROZEN}
    bad = {k: v for k, v in bad.items() if v != EXPECTED_FROZEN[k]}
    if bad: raise SystemExit('凍結コードのハッシュ不一致: ' + json.dumps(bad))
_frozen_ok()
sys.path.insert(0, os.path.join(FROZEN, 'src'))
def _imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(FROZEN, 'scripts', f)); m = importlib.util.module_from_spec(sp); sys.modules[n] = m; sp.loader.exec_module(m); return m
m51 = _imp('m51', '51_main_run_v3.py'); m52 = _imp('m52', '52_indices_v3.py')
from metriplectic_folding import make_native, kabsch_rmsd
# ---- 原典の dataclass MFDTrialSpec は evaluate/regenerate が使う最小フィールドのみ(原典: ns,a,D,seed,DT)。key() は原典と同一式 ----
from dataclasses import dataclass
@dataclass
class MFDTrialSpec:
    ns: int; a: float; D: float; seed: int; DT: float = 5e-3
    def key(self): return f"ns{self.ns}_a{self.a:g}_D{int(self.D)}_dt{self.DT:g}_s{self.seed}"
# === EXTRACTED (from controller; do not edit) ===
ARRAY_ORDER = ('U', 'D_inst', 'gnorm', 's', 'frame_step', 'frame_x', 'frame_Q', 'frame_rmsd_nat', 'frame_rmsd_mir', 'frame_dense', 'x_final', 'g_final')

def sha_bytes(b): return hashlib.sha256(b).hexdigest()

def sha_file(p):
    with open(p, 'rb') as f: return sha_bytes(f.read())

def arrays_hash(arr):
    h = hashlib.sha256()
    for k in ARRAY_ORDER: h.update(k.encode()); h.update(np.ascontiguousarray(arr[k]).tobytes())
    return h.hexdigest()

MAGIC = b'MFDM2\x01'

class M2Error(Exception): pass

def _unshuffle(b, dtype, shape):
    dt = np.dtype(dtype); n = int(np.prod(shape)) if len(shape) else 1
    if n == 0: return np.empty(shape, dt)
    return np.frombuffer(b, np.uint8).reshape(dt.itemsize, n).T.copy().view(dt).reshape(shape)

def m2_unpack(data: bytes) -> dict:
    if len(data) < len(MAGIC) + 8 + 32 or data[:len(MAGIC)] != MAGIC: raise M2Error('bad magic or truncated')
    body, tail = data[:-32], data[-32:]
    if hashlib.sha256(body).digest() != tail: raise M2Error('container checksum mismatch (corrupt or truncated)')
    (hl,) = struct.unpack('<Q', body[len(MAGIC):len(MAGIC) + 8]); off = len(MAGIC) + 8
    meta = json.loads(body[off:off + hl]); off += hl; out = {}
    for m in meta:
        c = body[off:off + m['clen']]; off += m['clen']
        try: b = lzma.decompress(c)
        except lzma.LZMAError as e: raise M2Error(f"lzma failure in {m['name']}: {e}")
        a = _unshuffle(b, m['dtype'], tuple(m['shape']))
        if sha_bytes(np.ascontiguousarray(a).tobytes()) != m['raw_sha256']: raise M2Error(f"array sha256 mismatch: {m['name']}")
        out[m['name']] = a
    if off != len(body): raise M2Error('trailing bytes')
    return out

def read_bytes(path):
    with open(path, 'rb') as f: return f.read()

def m2_read(path): return m2_unpack(read_bytes(path))

def tier1_arrays(summ, arr):
    fs = arr['frame_step']; DT = summ['DT']; ui = np.minimum(fs + 1, len(arr['U']) - 1); gi = np.minimum(fs, len(arr['gnorm']) - 1)
    return dict(frame_step=fs, frame_Q=arr['frame_Q'], frame_rmsd_nat=arr['frame_rmsd_nat'], frame_rmsd_mir=arr['frame_rmsd_mir'], frame_dense=arr['frame_dense'],
                U_at_frames=arr['U'][ui], gnorm_at_frames=arr['gnorm'][gi], x_final=arr['x_final'], g_final=arr['g_final'], U_every10=arr['U'][::int(round(0.05 / DT))])

def _jd(o): return o.item() if hasattr(o, 'item') else str(o)

def evaluate(spec: MFDTrialSpec, arr, summ):
    xn = make_native(m51.N, spec.ns); xf = arr['x_final'].astype(float); rn = kabsch_rmsd(xf, xn); rm = kabsch_rmsd(xf, xn * np.array([-1.0, 1, 1])); DT = spec.DT
    idx = m52.indices((arr['frame_step'] + 1) * DT, arr['frame_Q'], arr['frame_rmsd_nat'], arr['frame_rmsd_mir'], arr['U'], arr['gnorm'], DT)
    anomaly = (not np.isfinite(summ['U_end'])) or summ['max_dU'] > 1e-9 * max(1.0, abs(summ['U0']))
    cls = {str(t): m52.final_class(summ['grad_converged'], summ['U_end'], min(rn, rm), rn, rm, anomaly, t) for t in (0.01, 0.03, 0.1, 0.3)}
    return idx, cls

# === END EXTRACTED ===

# ================== 検証ロジック(新規作成。凍結コードの式は変更しない) ==================
SUFFIX = '_D500_dt0.0025_s0'
B_FULL = ['ns10_a16', 'ns12_a16', 'ns16_a16', 'ns17_a8', 'ns18_a16', 'ns18_a4', 'ns4_a16', 'ns4_a8', 'ns5_a16']
B_TIER1 = ['ns10_a4', 'ns12_a0', 'ns12_a4', 'ns12_a8', 'ns15_a4', 'ns16_a8', 'ns18_a8', 'ns2_a4', 'ns4_a4', 'ns9_a8']
THETAS = ('0.01', '0.03', '0.1', '0.3')
def load_ledger(path):
    rows = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.strip(): j = json.loads(line); rows[j['key']] = j
    return rows
def _spec(r): s = r['spec']; return MFDTrialSpec(int(s['ns']), float(s['a']), float(s['D']), int(s['seed']), float(s['DT']))
def _cmp_json(a, b):
    """原典の _jd で JSON 化した値の厳密一致(許容誤差なし)。"""
    return json.loads(json.dumps(a, default=_jd)) == json.loads(json.dumps(b, default=_jd))
def classes_of(spec, summ, xf):
    """tier-1 / 完全軌道の x_final から凍結関数で真の計算終端の構造量と分類を得る(最終保存フレームは使わない)"""
    xn = make_native(m51.N, spec.ns); xf = np.asarray(xf).astype(float)
    rn = kabsch_rmsd(xf, xn); rm = kabsch_rmsd(xf, xn * np.array([-1.0, 1, 1]))
    anomaly = (not np.isfinite(summ['U_end'])) or summ['max_dU'] > 1e-9 * max(1.0, abs(summ['U0']))
    cls = {str(t): m52.final_class(summ['grad_converged'], summ['U_end'], min(rn, rm), rn, rm, anomaly, t) for t in (0.01, 0.03, 0.1, 0.3)}
    return dict(rn_end=float(rn), rm_end=float(rm), m_end=float(min(rn, rm)), anomaly=bool(anomaly), classes=cls)
def verify_full(key, m2_path, ledger):
    r = ledger[key]; st = r['store']; out = dict(key=key, route='B-FULL')
    data = read_bytes(m2_path); out['file_sha256'] = sha_bytes(data); out['file_size'] = len(data)
    out['file_sha256_match'] = (out['file_sha256'] == st.get('full_sha256')); out['file_size_match'] = (len(data) == st.get('full_bytes'))
    arr = m2_unpack(data)    # 各配列と全体のチェックサムを内部で検査(失敗時 M2Error)
    out['n_arrays'] = len(arr); out['array_order_ok'] = tuple(arr.keys()) == ARRAY_ORDER or set(arr) == set(ARRAY_ORDER)
    out['content_hash'] = arrays_hash(arr); out['content_hash_match'] = (out['content_hash'] == r['arrays_sha256'])
    idx, cls = evaluate(_spec(r), arr, r['summary'])
    out['indices_match'] = _cmp_json(idx, r['indices']); out['classes'] = cls
    out['classes_match'] = {t: (cls[t] == r['classes'][t]) for t in THETAS}
    out['n_classes_match'] = sum(out['classes_match'].values())
    out['terminal'] = classes_of(_spec(r), r['summary'], arr['x_final'])
    out['terminal_classes_match'] = all(out['terminal']['classes'][t] == r['classes'][t] for t in THETAS)
    return out
def verify_tier1(key, npz_path, ledger):
    r = ledger[key]; st = r['store']; out = dict(key=key, route='B-TIER1'); out['file_size'] = os.path.getsize(npz_path); out['file_size_match'] = (out['file_size'] == st.get('tier1_bytes'))
    out['file_sha256'] = sha_file(npz_path)
    z = np.load(npz_path); out['keys'] = sorted(z.files)
    t = classes_of(_spec(r), r['summary'], z['x_final']); out['terminal'] = t
    out['classes_match'] = {k: (t['classes'][k] == r['classes'][k]) for k in THETAS}; out['n_classes_match'] = sum(out['classes_match'].values())
    out['note'] = 'tier-1 単独では元の12配列の内容ハッシュ(arrays_sha256)は再構成できない(U, D_inst, gnorm, s の全系列と frame_x を含まないため)'
    return out
def _bit_equal(a, b): return a.dtype == b.dtype and a.shape == b.shape and np.ascontiguousarray(a).tobytes() == np.ascontiguousarray(b).tobytes()
def regen_and_verify(key, npz_path, ledger):
    """B-REGEN: 凍結 trace_run で再生成(新規の研究ではなく既存条件の照合)。ビット一致と数値的近さを別々に記録(許容誤差による合格判定はしない)。"""
    r = ledger[key]; spec = _spec(r); out = dict(key=key, route='B-REGEN')
    summ, arr = m51.trace_run(spec.ns, spec.a, spec.seed, spec.D, spec.DT)
    out['n_arrays'] = len(ARRAY_ORDER); out['content_hash'] = arrays_hash(arr); out['content_hash_match'] = (out['content_hash'] == r['arrays_sha256'])
    out['array_bit_equal_vs_hash'] = None
    idx, cls = evaluate(spec, arr, summ)
    out['indices_match'] = _cmp_json(idx, r['indices']); out['classes_match'] = {t: (cls[t] == r['classes'][t]) for t in THETAS}; out['n_classes_match'] = sum(out['classes_match'].values())
    t1 = tier1_arrays(summ, arr); z = np.load(npz_path); eq = {k: _bit_equal(np.asarray(t1[k]), z[k]) for k in t1}
    out['tier1_array_bit_equal'] = eq; out['n_tier1_array_bit_equal'] = sum(eq.values()); out['n_tier1_arrays'] = len(eq)
    out['tier1_array_max_abs_diff'] = {k: (None if _bit_equal(np.asarray(t1[k]), z[k]) else (float(np.max(np.abs(np.asarray(t1[k], float) - z[k].astype(float)))) if np.asarray(t1[k]).shape == z[k].shape and z[k].size else 'SHAPE_MISMATCH')) for k in t1}   # 情報のみ。許容誤差による合格判定は行わない
    out['summary_match'] = _cmp_json({k: summ[k] for k in r['summary'] if k in summ}, r['summary'])
    out['env'] = dict(python=platform.python_version(), numpy=np.__version__, platform=platform.platform(), machine=platform.machine())
    out['recorded_env'] = r['recipe'].get('env')
    out['bit_identical_all'] = bool(out['content_hash_match'])
    return out
def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='MFD 独立照合(第三者実行用)')
    ap.add_argument('--ledger', required=True, help='凍結台帳 ledger.jsonl(SHA-256 5d4016da…b05f)')
    ap.add_argument('--full-dir'); ap.add_argument('--tier1-dir'); ap.add_argument('--regen', action='store_true')
    ap.add_argument('--out', required=True); a = ap.parse_args(argv)
    led = load_ledger(a.ledger); res = dict(ledger_sha256=sha_file(a.ledger), env=dict(python=platform.python_version(), numpy=np.__version__, platform=platform.platform()), results=[], status='RAW_RESULTS_ONLY(判定は第三者・編成統括)')
    if a.full_dir:
        for n in B_FULL:
            k = n + SUFFIX; p = os.path.join(a.full_dir, k + '.m2')
            res['results'].append(verify_full(k, p, led) if os.path.exists(p) else dict(key=k, route='B-FULL', error='FILE_NOT_FOUND'))
    if a.tier1_dir:
        for n in B_TIER1:
            k = n + SUFFIX; p = os.path.join(a.tier1_dir, k + '.npz')
            res['results'].append(verify_tier1(k, p, led) if os.path.exists(p) else dict(key=k, route='B-TIER1', error='FILE_NOT_FOUND'))
            if a.regen and os.path.exists(p): res['results'].append(regen_and_verify(k, p, led))
    with open(a.out, 'w', encoding='utf-8') as f: json.dump(res, f, ensure_ascii=False, indent=1, default=_jd)
    print('written', a.out)
if __name__ == '__main__': main()
