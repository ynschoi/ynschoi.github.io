# 몸 시트(JSON)에서 원래 머리를 지우고, 머리 부품(JSON)을 붙일 위치를 프레임마다 계산. 머리는 HEAD_SCALE로 줄여 저장.
# 사용: python3 attach.py heads.json 몸1.json [몸2.json ...]  → heads_s.json, 몸*_b.json
import json,sys
import numpy as np
HEAD_SCALE=.85;REF=18            # 몸 시트의 머리 폭(칸) 기준
dec=lambda s,w,h:np.array([(-1 if ch=='.' else ord(ch)-97) for ch in s]).reshape(h,w)
enc=lambda c:''.join('.' if v<0 else chr(97+v) for v in c.ravel())
def scale(c,k):                  # 면적 다수결 축소. 외곽선(0)이 1/3 넘으면 우선해서 선이 안 끊기게
    h,w=c.shape;H,W=max(1,round(h*k)),max(1,round(w*k));o=np.full((H,W),-1)
    for j in range(H):
        for i in range(W):
            b=c[int(j/k):max(int(j/k)+1,int((j+1)/k)),int(i/k):max(int(i/k)+1,int((i+1)/k))].ravel();v=np.bincount(b+1,minlength=9)
            if v[0]>b.size*.5:continue
            if v[1]>=b.size*.34:o[j,i]=0;continue
            vv=v.copy();vv[0]=vv[1]=0;o[j,i]=vv.argmax()-1 if vv.max()>0 else (0 if v[1]>0 else -1)
    return o
hd=json.load(open(sys.argv[1]));px,py,pw=hd['box'];nx,ny=hd['neck'];k=REF/pw*HEAD_SCALE
b=scale(dec(hd['base'],hd['w'],hd['h']),k)
json.dump({'w':int(b.shape[1]),'h':int(b.shape[0]),'base':enc(b),'layers':{n:enc(scale(dec(l,hd['w'],hd['h']),k)) for n,l in hd['layers'].items()}},open('heads_s.json','w'),separators=(',',':'))
for path in sys.argv[2:]:
    bd=json.load(open(path));BW,BH=bd['w'],bd['h'];fr=[];hp=[]
    for f in range(len(bd['f'])):
        c=dec(bd['f'][f],BW,BH);hx,hy,hw,hh=bd['head'][f];sk=np.isin(c,[0,1,2,21]);comp=np.zeros_like(sk);st=[(hy+1,hx+hw//2)]
        while st:
            y,x=st.pop()
            if 0<=y<hy+hh+1 and hx-3<=x<=hx+hw+3 and 0<=x<BW and sk[y,x] and not comp[y,x]:comp[y,x]=True;st+=[(y+1,x),(y-1,x),(y,x+1),(y,x-1)]
        c[comp]=-1;fr.append(enc(c));bx=hx+(nx-px)/pw*hw;by=hy+(ny-py)/pw*hw;hp.append([round(bx-nx*k),round(by-ny*k)])
    json.dump({'w':BW,'h':BH,'f':fr,'hp':hp},open(path.replace('.json','_b.json'),'w'),separators=(',',':'));print(path,hp)
