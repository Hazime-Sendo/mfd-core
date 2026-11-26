"""Rev.3 re-aggregation of the recovered 300-trial records. NO simulation. Input is read-only.
usage: python rev3_clip_and_bootstrap.py <path to dmax_sweep_runs.jsonl> <outdir>
Part A: clip_time * D_max / U0 per (a, D_max) cell.  Part B: seed-block bootstrap (10,000 replicates, fixed RNG seed)."""
import json,sys,os,math,hashlib,platform
import numpy as np
src,out=sys.argv[1],sys.argv[2]; os.makedirs(out,exist_ok=True)
rng_seed=20261124; B=10000
runs=[json.loads(l) for l in open(src)]
A=[0.0,1.0,4.0,8.0,16.0]; D=[200.,300.,400.,500.,700.,1000.]; S=list(range(10))
TERM={'NATIVE','MIRROR_TRAP','KINETIC_TRAP'}
idx={(r['a'],r['D_max'],r['seed']):r for r in runs}
assert len(idx)==300
log=[f"input sha256 {hashlib.sha256(open(src,'rb').read()).hexdigest()}",f"numpy {np.__version__} python {platform.python_version()} rng_seed {rng_seed} B {B}"]
# ---- Part A
rows=[];allr=[]
for a in A:
    for d in D:
        v=np.array([idx[(a,d,s)]['clip_time']*d/idx[(a,d,s)]['U0'] for s in S]); allr+=list(v)
        rows.append((a,d,len(v),v.mean(),v.std(ddof=1),v.min(),v.max(),v.mean()-1))
allr=np.array(allr)
cm=np.array([r[3] for r in rows])
log.append(f"A: 30 cells x 10 trials; cell-mean ratio min {cm.min():.4f} max {cm.max():.4f}; trial-level min {allr.min():.4f} max {allr.max():.4f}; mean {allr.mean():.4f}")
log.append(f"A: unfinished trials with clip_time recorded: {sum(r['state'] not in TERM for r in runs)}")
with open(os.path.join(out,'clip_ratio_cells.csv'),'w') as f:
    f.write('a,D_max,n,mean_ratio,sd,min,max,deviation_from_1\n')
    for r in rows: f.write(','.join(str(round(x,6)) if isinstance(x,float) else str(x) for x in r)+'\n')
# ---- Part B
def cellmeans(sel):  # sel: list of 10 seeds (with repetition). returns array [a][d] of mean t over terminal trials of selected seeds
    M=np.full((len(A),len(D)),np.nan)
    for i,a in enumerate(A):
        for j,d in enumerate(D):
            ts=[idx[(a,d,s)]['t'] for s in sel if idx[(a,d,s)]['state'] in TERM]
            if ts: M[i,j]=np.mean(ts)
    return M
def fit(m):
    x=1/np.array(D); X=np.vstack([x,np.ones_like(x)]).T
    if np.isnan(m).any(): return None
    c,*_=np.linalg.lstsq(X,m,rcond=None); r=m-X@c; cov=(r@r)/4*np.linalg.inv(X.T@X)
    return c[0],c[1],math.sqrt(cov[0,0]),math.sqrt(cov[1,1])
U0s=np.array([idx[(0.0,200.0,s)]['U0'] for s in S])
orig=[fit(cellmeans(S)[i]) for i in range(5)]
rng=np.random.default_rng(rng_seed)
sl=np.full((B,5),np.nan);ta=np.full((B,5),np.nan);u0=np.zeros(B);fail=0;failrec=[]
for b in range(B):
    sel=rng.integers(0,10,size=10).tolist(); sel=[S[k] for k in sel]
    M=cellmeans(sel); u0[b]=U0s[sel].mean()
    for i in range(5):
        f=fit(M[i])
        if f is None: failrec.append((b,A[i])); continue
        sl[b,i],ta[b,i]=f[0],f[1]
nf=len(failrec)
log.append(f"B: replicates {B}; inestimable (a,replicate) fits: {nf}; first few {failrec[:5]}")
res=[]
for i,a in enumerate(A):
    t=ta[:,i];s=sl[:,i];ok=~np.isnan(t)
    d=s[ok]-u0[ok]
    res.append(dict(a=a,tau_ols=orig[i][1],tau_se_ols=orig[i][3],tau_boot_mean=float(t[ok].mean()),tau_boot_sd=float(t[ok].std(ddof=1)),tau_ci=[float(np.percentile(t[ok],2.5)),float(np.percentile(t[ok],97.5))],
      slope_ols=orig[i][0],slope_se_ols=orig[i][2],slope_boot_mean=float(s[ok].mean()),slope_boot_sd=float(s[ok].std(ddof=1)),slope_ci=[float(np.percentile(s[ok],2.5)),float(np.percentile(s[ok],97.5))],
      slope_minus_U0_ci=[float(np.percentile(d,2.5)),float(np.percentile(d,97.5))],n_valid=int(ok.sum())))
ok=~np.isnan(ta[:,3])&~np.isnan(ta[:,4]); dd=ta[ok,4]-ta[ok,3]
res_extra=dict(tau16_minus_tau8_ols=orig[4][1]-orig[3][1],tau16_minus_tau8_ci=[float(np.percentile(dd,2.5)),float(np.percentile(dd,97.5))],frac_tau16_gt_tau8=float((dd>0).mean()),
  U0_mean=float(U0s.mean()),U0_boot_ci=[float(np.percentile(u0,2.5)),float(np.percentile(u0,97.5))],U0_sd_seeds=float(U0s.std(ddof=1)))
json.dump(dict(results=res,extra=res_extra,inestimable=nf,B=B,rng_seed=rng_seed),open(os.path.join(out,'bootstrap_results.json'),'w'),indent=1)
for r in res: log.append("a=%g tau OLS %.2f(se %.2f) boot sd %.2f CI [%.2f,%.2f]; slope OLS %.0f(se %.0f) boot sd %.0f CI [%.0f,%.0f]; slope-U0 CI [%.0f,%.0f]; valid %d"%(r['a'],r['tau_ols'],r['tau_se_ols'],r['tau_boot_sd'],*r['tau_ci'],r['slope_ols'],r['slope_se_ols'],r['slope_boot_sd'],*r['slope_ci'],*r['slope_minus_U0_ci'],r['n_valid']))
log.append(str(res_extra))
open(os.path.join(out,'bootstrap_log.txt'),'w').write('\n'.join(log)+'\n'); print('\n'.join(log))
