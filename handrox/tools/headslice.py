# 머리 부품 시트(4x2, 칸마다 머리+부품) → 민머리 + 부품 레이어(JSON). 사용: python3 headslice.py 시트.png 이름
import sys,json
from PIL import Image
import numpy as np
src,name=sys.argv[1],sys.argv[2];N=64
a=np.array(Image.open(src).convert('RGBA')).astype(int);H,W=a.shape[:2]
PAL=[(32,32,40),(242,184,146),(201,138,98),(255,255,0),(200,200,0),(140,140,0),(255,255,255),(0,0,0),(95,90,10)]
pal=np.array(PAL);d=((a[...,:3][:,:,None,:]-pal[None,None])**2).sum(3);cl=d.argmin(2);cl[cl==7]=0;cl[cl==8]=5;cl[a[...,3]<110]=-1
g=np.full((N*2,N*4),-1)
for j in range(N*2):
    y0,y1=int(j*H/(N*2)),int((j+1)*H/(N*2))
    for i in range(N*4):
        x0,x1=int(i*W/(N*4)),int((i+1)*W/(N*4));v=np.bincount(cl[y0:y1,x0:x1].ravel()+1,minlength=8);g[j,i]=v.argmax()-1
cells=[g[(f//4)*N:(f//4+1)*N,(f%4)*N:(f%4+1)*N].copy() for f in range(8)]
base=cells[0];bsk=(base==1)|(base==2)
def shift(c,dy,dx):
    o=np.full_like(c,-1);ys=slice(max(0,dy),min(N,N+dy));xs=slice(max(0,dx),min(N,N+dx));o[ys,xs]=c[max(0,-dy):min(N,N-dy),max(0,-dx):min(N,N-dx)];return o
names=['bald','short','mid','long','cap','band','sun','visor'];layers={}
for f in range(1,8):
    best=(-1,0,0)
    for dy in range(-8,9):
        for dx in range(-8,9):
            s=shift(cells[f],dy,dx);sc=(((s==1)|(s==2))&bsk).sum()-(((s==1)|(s==2))&(base<0)).sum()
            if sc>best[0]:best=(sc,dy,dx)
    c=shift(cells[f],best[1],best[2]);item=np.isin(c,[3,4,5])
    near=np.zeros_like(item)                                  # 부품에 붙은 외곽선만 부품 것으로 (민머리에 없던 선)
    for dy,dx in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):near|=shift(item.astype(int),dy,dx)==1
    ol=(c==0)&near&(base!=0)
    L=np.full_like(c,-1);L[item]=c[item];L[ol]=0;layers[names[f]]=L;print(names[f],'shift',best[1:],'px',int(item.sum()))
ys,xs=np.where((base>=0)|np.any([l>=0 for l in layers.values()],axis=0));y0,y1,x0,x1=ys.min(),ys.max()+1,xs.min(),xs.max()+1
enc=lambda c:''.join('.' if v<0 else chr(97+v) for v in c[y0:y1,x0:x1].ravel())
sy=np.where(bsk.any(1))[0];ty=sy[0];hx=[x for x in range(N) if bsk[ty:ty+9,x].any()];bot=np.where((base>=0).any(1))[0][-1];nx=np.where(base[bot]>=0)[0]
out={'w':int(x1-x0),'h':int(y1-y0),'base':enc(base),'box':[int(hx[0]-x0),int(ty-y0),int(hx[-1]-hx[0]+1)],'neck':[float(nx.mean()-x0),int(bot-y0)],'layers':{k:enc(v) for k,v in layers.items()}}
json.dump(out,open(name+'.json','w'),separators=(',',':'));print(out['w'],out['h'],out['box'],out['neck'])
COL=[(38,38,46),(242,184,146),(201,138,98),(229,57,31),(170,40,22),(110,26,14),(255,255,255)]
im=Image.new('RGB',((x1-x0)*8,(y1-y0)),(5,5,6))
def put(c,ox):
    for (j,i),v in np.ndenumerate(c[y0:y1,x0:x1]):
        if v>=0:im.putpixel((ox+i,j),COL[v])
put(base,0)
for k,(n_,l) in enumerate(layers.items()):put(base,(k+1)*(x1-x0));put(l,(k+1)*(x1-x0))
im.resize((im.width*4,im.height*4),Image.NEAREST).save(name+'_prev.png')
