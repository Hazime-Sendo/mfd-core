# 環境確認スクリプト(読取のみ)。python tools/check_env.py
import sys, platform, hashlib, os, json
info={"python":sys.version,"platform":platform.platform(),"machine":platform.machine(),"processor":platform.processor() or None}
try:
    import numpy; info["numpy"]=numpy.__version__
except Exception as e: info["numpy"]=f"MISSING: {e}"
ok = sys.version_info>=(3,11) and not str(info["numpy"]).startswith("MISSING")
info["python_ge_3_11"]=sys.version_info>=(3,11)
print(json.dumps(info,ensure_ascii=False,indent=1)); print("ENV_OK" if ok else "ENV_NG"); sys.exit(0 if ok else 1)
