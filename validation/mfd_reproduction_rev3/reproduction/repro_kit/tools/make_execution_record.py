# 実行記録(第三者実行用)を作る。 python tools/make_execution_record.py <実行者名> <logs/名前>  -> logs/<名前>_execution_record.json
import sys, json, hashlib, datetime, platform, os
who,tag=sys.argv[1],sys.argv[2]
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def sha(p): return hashlib.sha256(open(p,"rb").read()).hexdigest() if os.path.exists(p) else None
rec={"executor":who,"executed_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "platform":platform.platform(),"python":sys.version,
 "input_evidence_before_sha256":sha(os.path.join(root,f"{tag}_evidence_before.txt")) if os.path.isabs(tag) else sha(os.path.join(root,tag+"_evidence_before.txt")),
 "outputs_sha256":{n:sha(os.path.join(root,n)) for n in [tag+s for s in ("_stdout.txt","_stderr.txt","_exit.txt","_env.txt","_evidence_after.txt")]},
 "note":"本人実行は『環境間再現』、独立した第三者による実行のみ『第三者再現』と区別して記録する"}
out=os.path.join(root,tag+"_execution_record.json")
with open(out,"w",encoding="utf-8") as f: json.dump(rec,f,ensure_ascii=False,indent=1)
print(out)
