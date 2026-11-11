# AI로 받은 4x2 시트 → 정확한 격자의 색 번호 스프라이트(JSON). 사용: python3 slice.py 시트.png 이름
# 칸마다 96x64로 줄이고(다수결), 지정 팔레트로 맞춤. 머리 상자를 프레임마다 찾아 함께 저장.
import sys,json
from PIL import Image
import numpy as np
src,name=sys.argv[1],sys.argv[2];CW,CH=96,64
a=np.array(Image.open(src).convert('RGBA')).astype(int);H,W=a.shape[:2]
PAL=['#202028','#F2B892','#C98A62','#FF0000','#A80000','#0000FF','#0000A8','#00FFFF','#00A8A8','#00FF00','#00A800','#FF00FF','#A800A8','#FFFFFF','#BBBBBB','#3A3A44','#26262E','#FFD400','#C8C8D0','#000000','#D9A02A','#FFFFFF']
pal=np.array([[int(h[i:i+2],16) for i in (1,3,5)] for h in PAL[:21]])
d=((a[...,:3][:,:,None,:]-pal[None,None])**2).sum(3);cl=d.argmin(2);cl[cl==19]=0;cl[a[...,3]<110]=-1
GW,GH=CW*4,CH*2;g=np.full((GH,GW),-1)
for j in range(GH):
    y0,y1=int(j*H/GH),int((j+1)*H/GH)
    for i in range(GW):
        x0,x1=int(i*W/GW),int((i+1)*W/GW);v=np.bincount(cl[y0:y1,x0:x1].ravel()+1,minlength=22);g[j,i]=v.argmax()-1
frames=[];heads=[]
for f in range(8):
    c=g[(f//4)*CH:(f//4+1)*CH,(f%4)*CW:(f%4+1)*CW].copy();sk=(c==1)|(c==2)
    ty=int(np.where(sk.any(1))[0][0]);tx=int(np.where(sk[ty])[0][0]);comp=np.zeros_like(sk);st=[(ty,tx)]
    body=(c>=0)&~np.isin(c,[15,16,17,18,20])          # 머리 = 맨 위에서 이어진 살색+외곽선 덩어리 중 목 위
    while st:
        y,x=st.pop()
        if 0<=y<CH and 0<=x<CW and (sk[y,x] or (c[y,x]==0 and y<ty+30)) and not comp[y,x]:comp[y,x]=True;st+=[(y+1,x),(y-1,x),(y,x+1),(y,x-1)]
    ys=np.where(comp.any(1))[0];wd=[int(sk[y].sum()) for y in range(ty,min(CH,ty+34))];hh=len(wd);mx=0
    for q in range(len(wd)):
        mx=max(mx,wd[q])
        if q>8 and wd[q]<mx*.55:hh=q;break
    hx=[x for x in range(CW) if sk[ty:ty+min(hh,9),x].any()];hw=hx[-1]-hx[0]+1;hh=hw;head=[hx[0],ty,hw,hh];heads.append(head)   # 눈·눈썹 때문에 폭이 끊겨서 높이는 폭과 같게 잡음
    hb=c[ty:ty+hh+3,hx[0]:hx[-1]+3];hb[(hb==13)|(hb==14)]=21           # 눈 흰자·이는 신발 색과 분리
    so=np.argwhere((c==11)|(c==12))                                      # 양말에서 먼 흰색·회색은 신발이 아니라 장비 금속
    for y,x in np.argwhere((c==13)|(c==14)):
        if not len(so) or np.abs(so-[y,x]).sum(1).min()>12:c[y,x]=18
    frames.append(''.join('.' if v<0 else chr(97+v) for v in c.ravel()))
json.dump({'w':CW,'h':CH,'f':frames,'head':heads},open(name+'.json','w'),separators=(',',':'))
out=Image.new('RGB',(GW*4,GH*4),(5,5,6))
for f in range(8):
    im=Image.new('RGB',(CW,CH),(5,5,6))
    for i,chx in enumerate(frames[f]):
        if chx!='.':im.putpixel((i%CW,i//CW),tuple(int(PAL[ord(chx)-97][k:k+2],16) for k in (1,3,5)))
    hx,hy,hw,hh=heads[f]
    for x in range(hx,hx+hw):
        for y in (hy,hy+hh-1):im.putpixel((x,y),(255,0,255))
    out.paste(im.resize((CW*4,CH*4),Image.NEAREST),((f%4)*CW*4,(f//4)*CH*4))
out.save(name+'_prev.png');print(heads)
