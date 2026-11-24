"""A2 Provenance Gate. Five independent fields; byte-integrity never implies authenticity or approval."""
import json
GATE_B_EXPECTED = {"aux_timing_33_candidate.csv": "fe2dbf7f", "mfd_rbsh_v2_freeze_manifest.sha256": "b02a7294"}  # prefixes from spec
GATE_B_FULL_SUFFIX = {"aux_timing_33_candidate.csv": "ae6925f", "mfd_rbsh_v2_freeze_manifest.sha256": "910830"}

def assess(ev, hmac_key=None):
    out = {}
    bad = [r.name for r in ev.records.values() if r.integrity in ("HASH_MISMATCH", "MISSING")]
    out["byte_integrity"] = {"state": "VERIFIED" if not bad else "NOT VERIFIED",
        "scope": "bytes match SHA256SUMS.txt shipped inside the same bundle (self-referential; not an independent root of trust)",
        "problems": bad}
    # authenticity: HMAC needs a key which Claude does not hold; recomputation is not possible
    auths = [n for n in ev.records if "authorization" in n]
    out["hmac_authenticity"] = {"state": "NOT VERIFIED", "reason": "HMAC key not supplied; mac fields present but cannot be recomputed" if hmac_key is None else "key supplied but verification not implemented in analysis-only scope",
        "files_with_mac": auths}
    # approval state as written in manifests (reported, not adjudicated)
    st = {}
    for n in sorted(ev.records):
        if n.endswith(".json") and "manifest" in n:
            try:
                o = ev.load_json(n)
                st[n] = {k: o[k] for k in ("execution_status", "approvals") if k in o}
            except Exception as e: st[n] = {"error": str(e)}
    out["approval_state"] = {"state": "NOT VERIFIED", "as_written_in_manifests": st,
        "note": "approval state A-D is unresolved; discrepancy between manifests is reported, not resolved"}
    # prep manifest vs execution record relation
    out["manifest_vs_execution"] = {"state": "REVIEW", "note": "B_preparation manifest and execution manifest coexist; relation not adjudicated here"}
    # Gate B missing inputs: search by hash prefix among all shipped files
    found = {}
    for want, pre in GATE_B_EXPECTED.items():
        hits = [r.name for r in ev.records.values() if r.sha256.startswith(pre) and r.sha256.endswith(GATE_B_FULL_SUFFIX[want])]
        found[want] = hits
    out["gate_b_missing_inputs"] = {"state": "NOT VERIFIED", "expected_prefix_suffix": {k: [GATE_B_EXPECTED[k], GATE_B_FULL_SUFFIX[k]] for k in GATE_B_EXPECTED}, "matches_in_bundle": found,
        "note": "no substitute file with a different hash is accepted"}
    return out
