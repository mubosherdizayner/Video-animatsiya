import numpy as np, sys, os, json
from PIL import Image, ImageFilter
from scipy import ndimage as ndi
U="/root/.claude/uploads/6ade38c6-ce42-51f9-865c-81980e418fea/"
OUT=sys.argv[1]
SHEETS={"bobur":(U+"0aa7647d-image.jpg",4,3),"cust":(U+"8998f1c2-image.png",4,3)}
TOL=18
def segments(p, thr, minlen=3):
    on=p>thr; segs=[]; i=0; n=len(p)
    while i<n:
        if on[i]:
            j=i
            while j<n and on[j]: j+=1
            if j-i>=minlen: segs.append([i,j])
            i=j
        else: i+=1
    return segs
def merge_to(segs,k):
    segs=[list(s) for s in segs]
    while len(segs)>k:
        gaps=[segs[i+1][0]-segs[i][1] for i in range(len(segs)-1)]
        i=int(np.argmin(gaps)); segs[i]=[segs[i][0],segs[i+1][1]]; del segs[i+1]
    return segs
meta={}
for name,(path,nc,nr) in SHEETS.items():
    im=np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    bg=np.median(im[::4,::4].reshape(-1,3),axis=0)
    d=np.abs(im-bg).max(2); fg=d>TOL
    rs=merge_to(segments(fg.mean(1),0.002),nr)
    idx=0
    for r0,r1 in rs:
        band=fg[r0:r1]
        cs=merge_to(segments(band.mean(0),0.0,2),nc)
        for c0,c1 in cs:
            idx+=1
            P=6
            y0,y1=max(r0-P,0),min(r1+P,im.shape[0]); x0,x1=max(c0-P,0),min(c1+P,im.shape[1])
            cell=im[y0:y1,x0:x1]; dd=d[y0:y1,x0:x1]
            near=dd<=TOL
            lab,n=ndi.label(near)
            border=set(np.unique(np.concatenate([lab[0],lab[-1],lab[:,0],lab[:,-1]])))-{0}
            bgm=np.isin(lab,list(border))
            # enclosed holes of flat background (between arm and body)
            tight=dd<=7
            lab2,n2=ndi.label(tight)
            sizes=ndi.sum(np.ones_like(dd),lab2,index=np.arange(1,n2+1))
            for li,sz in enumerate(sizes,1):
                if sz>=12:
                    m=lab2==li
                    if not bgm[m].all():
                        # flat-grey check: inside pixels close to bg
                        if (dd[m]<=7).mean()>0.98:
                            mm=ndi.binary_dilation(m,iterations=2)&near
                            bgm|=mm
            # grow bg by 1 px to drop antialias fringe
            bgg=ndi.binary_dilation(bgm,iterations=1)
            keep=~bgg
            labk,nk=ndi.label(keep)
            if nk>1:
                szk=ndi.sum(np.ones_like(dd),labk,index=np.arange(1,nk+1))
                for li,sz in enumerate(szk,1):
                    if sz<25: keep[labk==li]=False
            alpha=keep.astype(np.float32)
            # keep largest components + small ones near (tears etc.)
            a8=Image.fromarray((alpha*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
            rgba=np.dstack([cell.astype(np.uint8),np.asarray(a8)])
            spr=Image.fromarray(rgba,"RGBA")
            bb=spr.getbbox(); spr=spr.crop((max(bb[0]-6,0),max(bb[1]-6,0),min(bb[2]+6,spr.width),min(bb[3]+6,spr.height)))
            ow,oh=spr.size
            up=spr.convert("RGBa").resize((ow*4,oh*4),Image.LANCZOS).convert("RGBA")
            rgb=up.convert("RGB").filter(ImageFilter.UnsharpMask(radius=2,percent=60,threshold=2))
            up=Image.merge("RGBA",(*rgb.split(),up.getchannel("A")))
            up.save(f"{OUT}/{name}_{idx:02d}.png")
            meta[f"{name}_{idx:02d}"]={"cell":[int(x1-x0),int(y1-y0)],"orig":[ow,oh],"up":[ow*4,oh*4]}
json.dump(meta,open(f"{OUT}/meta.json","w"),indent=1)
print(len(meta),"sprites")
