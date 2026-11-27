import sys,json,csv,os
out,exp=sys.argv[1],json.load(open(sys.argv[2]))
rows=list(csv.DictReader(open(os.path.join(out,'clip_ratio_cells.csv'))))
r=[float(x['mean_ratio']) for x in rows]; tol=exp['tolerance']
ok=len(rows)==30 and abs(min(r)-exp['cell_mean_ratio_min'])<tol and abs(max(r)-exp['cell_mean_ratio_max'])<tol
print('clip ratio cell means: n=%d min=%.4f max=%.4f expected %.4f..%.4f tol %g -> %s'%(len(rows),min(r),max(r),exp['cell_mean_ratio_min'],exp['cell_mean_ratio_max'],tol,'OK' if ok else 'DIFF'))
sys.exit(0 if ok else 1)
