import numpy as np,json
from PIL import Image,ImageFilter
S='/tmp/claude-0/-home-user/5ea83b1b-a164-5d78-aa25-8867aec9cf30/scratchpad'
o=np.asarray(Image.open(S+'/oF2/hturn_0_c.png').convert('RGBA')).astype(float)
b=np.asarray(Image.open(S+'/bF2/hturn_0_c.png').convert('RGBA')).astype(float)
f=np.asarray(Image.open(S+'/bF2/hturn_0_f.png').convert('RGBA')).astype(float)
H,W=o.shape[:2];FTW,FTH=512,360
lum=lambda a:a[...,0]*.3+a[...,1]*.59+a[...,2]*.11
valid=(f[...,3]>128)&(o[...,3]>128)&(b[...,3]>128)
d=np.abs(o[...,:3]-b[...,:3]).sum(-1)
feat=valid&(d>40)
print('feat px',feat.sum(),'valid',valid.sum())
# shading the game will apply: sh=min(1.12,lum(base)/205) -> texture colour = orig/sh
sh=np.clip(lum(b)/205,.2,1.12)[...,None]
col=np.clip(o[...,:3]/sh,0,255)
# alpha: soft by difference strength
al=np.clip((d-25)/70,0,1)*valid
tex=np.zeros((FTH,FTW,4));wsum=np.zeros((FTH,FTW))
ys,xs=np.nonzero(valid&(al>0))
u=(f[ys,xs,0]/255*FTW).astype(int).clip(0,FTW-1);v=(f[ys,xs,1]/255*FTH).astype(int).clip(0,FTH-1)
for yy,xx,uu,vv in zip(ys,xs,u,v):
    w=1.0;tex[vv,uu,:3]+=col[yy,xx]*w;tex[vv,uu,3]+=al[yy,xx]*w;wsum[vv,uu]+=w
m=wsum>0;tex[m,:3]/=wsum[m][:,None];tex[m,3]/=wsum[m]
# fill small holes (texture is splatted): dilate by averaging neighbours where empty
img=Image.fromarray(np.dstack([tex[...,:3],tex[...,3]*255]).clip(0,255).astype(np.uint8),'RGBA')
for _ in range(2):
    a=np.asarray(img).astype(float);emp=a[...,3]==0
    nb=np.zeros_like(a);cnt=np.zeros(a.shape[:2])
    for dy,dx in ((0,1),(0,-1),(1,0),(-1,0)):
        s=np.roll(np.roll(a,dy,0),dx,1);ok=s[...,3]>0;nb[ok]+=s[ok];cnt+=ok
    fill=emp&(cnt>=2);a[fill]=nb[fill]/cnt[fill][:,None];img=Image.fromarray(a.clip(0,255).astype(np.uint8),'RGBA')
img.save(S+'/face_orig_full.png')
a=np.asarray(img);A=a[...,3]>40
ys,xs=np.nonzero(A);print('bbox',xs.min(),xs.max(),ys.min(),ys.max())
# row histogram to find bands
rows=A.sum(1);print([ (i,int(r)) for i,r in enumerate(rows) if r>0][::4])
