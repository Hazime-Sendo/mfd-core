# 2つの実行結果ディレクトリ(out_*)を比較する。python tools/compare_runs.py outA outB
# ラベル再構成はバイト一致を要求。analysis_report.json は environment を除き、浮動小数は相対 1e-9 まで許容(差は表示)。
import json, sys, os, math
a,b=sys.argv[1],sys.argv[2]
la=open(os.path.join(a,"label_reconstruction_140.json"),"rb").read(); lb=open(os.path.join(b,"label_reconstruction_140.json"),"rb").read()
print("labels byte-identical:", la==lb)
A=json.load(open(os.path.join(a,"analysis_report.json"),encoding="utf-8")); B=json.load(open(os.path.join(b,"analysis_report.json"),encoding="utf-8"))
diffs=[]
def walk(x,y,p=""):
    if isinstance(x,dict) and isinstance(y,dict):
        for k in sorted(set(x)|set(y)):
            if p=="" and k=="environment": continue
            walk(x.get(k),y.get(k),p+"/"+str(k))
    elif isinstance(x,list) and isinstance(y,list) and len(x)==len(y):
        for i,(u,v) in enumerate(zip(x,y)): walk(u,v,p+f"[{i}]")
    elif isinstance(x,float) and isinstance(y,float):
        if x!=y: diffs.append((p,x,y,abs(x-y)/max(abs(x),abs(y),1e-300)))
    elif x!=y: diffs.append((p,x,y,None))
walk(A,B)
hard=[d for d in diffs if d[3] is None or d[3]>1e-9]
for d in diffs: print("diff",d)
print("non-numeric or >1e-9 differences:",len(hard))
sys.exit(0 if la==lb and not hard else 1)
