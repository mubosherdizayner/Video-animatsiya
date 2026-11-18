import json, re, difflib, numpy as np, sys
from script_data import SCENES
APOS = "ʻʼ'`‘’ʹ′"
def norm(w):
    w=w.lower()
    for a in APOS: w=w.replace(a,"'")
    return re.sub(r"[^a-z']","",w)
def fold(w):
    w=norm(w).replace("o'","o").replace("g'","g").replace("'","")
    w=w.replace("kh","h").replace("x","h").replace("q","k").replace("sh","s").replace("ch","c").replace("ng","n")
    w=re.sub(r"[aeiou]","a",w)
    return w
def sim(a,b): return difflib.SequenceMatcher(None,fold(a),fold(b)).ratio()
def align(script_words, tr):
    n,m=len(script_words),len(tr)
    INF=1e9; D=np.full((n+1,m+1),INF); B={}
    D[0,0]=0
    for i in range(n+1):
        for j in range(m+1):
            if D[i,j]>=INF: continue
            c=D[i,j]
            opts=[]
            if i<n and j<m: opts.append((i+1,j+1,1-sim(script_words[i],tr[j]['w']),'11'))
            if i+1<n and j<m: opts.append((i+2,j+1,1-sim(script_words[i]+script_words[i+1],tr[j]['w'])+0.3,'21'))
            if i<n and j+1<m: opts.append((i+1,j+2,1-sim(script_words[i],tr[j]['w']+tr[j+1]['w'])+0.3,'12'))
            if i<n: opts.append((i+1,j,0.9,'s0'))
            if j<m: opts.append((i,j+1,0.9,'0t'))
            for a,b,cost,k in opts:
                if c+cost<D[a,b]: D[a,b]=c+cost; B[(a,b)]=(i,j,k)
    path=[]; a,b=n,m
    while (a,b)!=(0,0):
        i,j,k=B[(a,b)]; path.append((i,j,k)); a,b=i,j
    return path[::-1]
def main(words_json, db_npy, out):
    tr=json.load(open(words_json))
    sw=[]; 
    for sid,spk,txt in SCENES:
        for k,w in enumerate(txt.split()): sw.append({"scene":sid,"speaker":spk,"text":w,"first":k==0})
    path=align([w['text'] for w in sw],tr)
    times=[None]*len(sw)
    for i,j,k in path:
        if k=='11' and sim(sw[i]['text'],tr[j]['w'])>0.35: times[i]=[tr[j]['s'],tr[j]['e'],'m']
        elif k=='21':
            s,e=tr[j]['s'],tr[j]['e']; l1,l2=len(norm(sw[i]['text'])),len(norm(sw[i+1]['text']))
            mid=s+(e-s)*l1/(l1+l2); times[i]=[s,mid,'split']; times[i+1]=[mid,e,'split']
        elif k=='12': times[i]=[tr[j]['s'],tr[j+1]['e'],'m2']
    # interpolate unmatched
    for i in range(len(sw)):
        if times[i] is None:
            p=max([k for k in range(i) if times[k]],default=None); q=min([k for k in range(i+1,len(sw)) if times[k]],default=None)
            t0=times[p][1] if p is not None else 0.0; t1=times[q][0] if q is not None else t0+0.5
            cnt=(q if q is not None else len(sw))-(p if p is not None else -1)-1; pos=i-(p if p is not None else -1)
            ds=(t1-t0)/(cnt+0)*0 + (t1-t0)/(cnt) 
            times[i]=[t0+ds*(pos-1),t0+ds*pos,'interp']
    # refine onsets with energy: snap start to end of a preceding silence run
    db=np.load(db_npy); hop=0.005; mx=db.max(); sil=db<mx-38
    runs=[];i=0;n=len(sil)
    while i<n:
        if sil[i]:
            j=i
            while j<n and sil[j]: j+=1
            if (j-i)*hop>=0.06: runs.append((i*hop+0.01,j*hop+0.01))
            i=j
        else: i+=1
    for k,w in enumerate(sw):
        s,e,how=times[k]
        prev_s=times[k-1][0] if k else -1
        cands=[r for r in runs if s-0.15<=r[1]<=s+0.45 and r[0]<=s+0.06 and r[1]<e-0.08 and r[1]>prev_s+0.05]
        if cands:
            ns=min(cands,key=lambda r:r[1])[1]
            times[k][0]=round(ns,3); times[k][2]=how+'+snap'
            if k and times[k-1][1]>ns: times[k-1][1]=ns
    times[0][0]=0.0
    for k,w in enumerate(sw): w['start'],w['end'],w['how']=round(times[k][0],3),round(times[k][1],3),times[k][2]
    json.dump(sw,open(out,'w'),ensure_ascii=False,indent=1)
    for w in sw: print(f"{w['scene']:>2} {w['text']:<16} {w['start']:6.2f} {w['end']:6.2f} {w['how']}")
if __name__=="__main__": main(*sys.argv[1:4])
