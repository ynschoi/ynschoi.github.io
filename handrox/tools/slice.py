# AI 시트 → 저해상도 구역 스프라이트. 사용: python3 slice.py row_raw.png row 12 42 26 30
import sys,json
from PIL import Image
import numpy as np
src,name,BS,SW,SH,MX=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5]),int(sys.argv[6])
a=np.array(Image.open(src).convert('RGBA')).astype(int);H,W=a.shape[:2]
REF={'K':(0,0,0),'M':(28,28,28),'S':(244,180,140),'R':(240,0,0),'B':(0,0,235),'C':(0,200,240),'G':(0,200,20),'Y':(245,205,0),'W':(240,240,240),'E':(190,190,190)}
keys=list(REF);ref=np.array([REF[k] for k in keys])
d=((a[...,:3][:,:,None,:]-ref[None,None])**2).sum(3);cl=d.argmin(2);cl[a[...,3]<128]=-1
cw,ch=W//4,H//2;frames=[];heads=[]
for f in range(8):
    cx,cy=(f%4)*cw,(f//4)*ch;cell=cl[cy:cy+ch,cx:cx+cw]
    xs=np.where((cell>=0).any(0))[0];ys=np.where((cell>=0).any(1))[0];x1,y1=xs.max()+1,ys.max()+1   # 장비 오른쪽·아래 기준 정렬
    g=[]
    for j in range(SH):
        row=''
        for i in range(SW):
            px0,py0=x1-(SW-i)*BS,y1-(SH-j)*BS;b=cell[max(0,py0):max(0,py0+BS),max(0,px0):max(0,px0+BS)].ravel()
            if b.size==0:row+='.';continue
            v=np.bincount(b+1,minlength=len(keys)+1);k=v.argmax();row+='.' if k==0 else keys[k-1]
        g.append(row)
    g=[''.join('y' if c=='Y' and i>=MX else c for i,c in enumerate(r)) for r in g]      # 장비 노랑 / 양말 노랑 구분
    frames.append(g)
    sk=np.array([[c=='S' for c in r] for r in g]);ty=int(np.where(sk.any(1))[0][0]);tx=int(np.where(sk[ty])[0][0])
    comp=np.zeros_like(sk);st=[(ty,tx)]                                   # 맨 위 살색에서 시작해 이어진 덩어리
    while st:
        y,x=st.pop()
        if 0<=y<SH and 0<=x<SW and sk[y,x] and not comp[y,x]:comp[y,x]=True;st+=[(y+1,x),(y-1,x),(y,x+1),(y,x-1)]
    ys=np.where(comp.any(1))[0];wd=[int(comp[y].sum()) for y in range(ys[0],ys[-1]+1)];hh=len(wd)
    for q in range(3,len(wd)):
        if wd[q]<max(wd[:q])*.6:hh=q;break
    hx=[x for x in range(SW) if comp[ys[0]:ys[0]+hh,x].any()]
    heads.append([hx[0],int(ys[0]),hx[-1]-hx[0]+1,hh])
json.dump({'w':SW,'h':SH,'f':[''.join(g) for g in frames],'head':heads},open(name+'.json','w'))
PAL={'.':(5,5,6),'K':(11,11,14),'M':(52,52,60),'S':(141,90,59),'R':(229,57,31),'B':(229,57,31),'C':(141,90,59),'G':(42,42,50),'Y':(242,242,242),'y':(255,212,0),'W':(53,196,106),'E':(190,190,190)}
Z=6;out=Image.new('RGB',(SW*Z*4,SH*Z*2))
for f,g in enumerate(frames):
    im=Image.new('RGB',(SW,SH))
    for j,r in enumerate(g):
        for i,c in enumerate(r):im.putpixel((i,j),PAL[c])
    hx,hy,hw,hh=heads[f]
    for i in range(hx-1,hx+hw):                      # 머리카락·반다나 시험
        for j in range(hy-1,hy+3):
            if 0<=i<SW and 0<=j<SH:im.putpixel((i,j),(42,32,24))
    for i in range(hx-1,hx+hw+1):
        if 0<=i<SW:im.putpixel((i,hy+3),(255,212,0))
    out.paste(im.resize((SW*Z,SH*Z),Image.NEAREST),((f%4)*SW*Z,(f//4)*SH*Z))
out.save(name+'_prev.png');print(heads)
