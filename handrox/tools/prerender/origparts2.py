import numpy as np,json
from PIL import Image,ImageFilter
S='/tmp/claude-0/-home-user/5ea83b1b-a164-5d78-aa25-8867aec9cf30/scratchpad'
a=np.asarray(Image.open(S+'/face_orig_full.png').convert('RGBA')).astype(float);H,W=a.shape[:2]
# 가운데 이음선: 열마다 바로 옆 열들과 많이 다르면 양옆 평균으로
L,R=a[:,251].copy(),a[:,260].copy()
for x in range(252,260):
    t=(x-251)/9;a[:,x]=L*(1-t)+R*t
al=a[...,3]/255
strong=al>.45
# 연결 요소
from collections import deque
lab=np.zeros((H,W),int);n=0;info=[]
for y in range(H):
    for x in range(W):
        if strong[y,x] and not lab[y,x]:
            n+=1;q=deque([(y,x)]);lab[y,x]=n;pts=[]
            while q:
                cy,cx=q.popleft();pts.append((cy,cx))
                for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    yy,xx=cy+dy,cx+dx
                    if 0<=yy<H and 0<=xx<W and strong[yy,xx] and not lab[yy,xx]:lab[yy,xx]=n;q.append((yy,xx))
            p=np.array(pts);info.append((n,len(pts),p[:,0].mean(),p[:,1].mean(),p[:,0].min(),p[:,0].max(),p[:,1].min(),p[:,1].max()))
big=[i for i in info if i[1]>150]
for i in big:print([round(v) for v in i])
def part(c):
    _,_,cy,cx,*_=c
    if cy<25 or cy>330:return None
    if cy<85:return 'b'
    if cy<190 and (cx<200 or cx>310):return 'e'
    if cy<255 and 200<=cx<=310:return 'n'
    if cy>=245:return 'm'
    return None
ORD=['b','e','n','m'];out=np.zeros((H*4,W,4),np.uint8);boxes={}   # 부위마다 따로 한 층(위에서부터 눈썹·눈·코·입) → 상자가 겹쳐도 다른 부위가 섞이지 않음
for c in big:
    k=part(c)
    if not k:continue
    m=lab==c[0]
    mi=np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)))>0   # 가장자리 부드러운 테두리까지
    sel=mi&(al>.15)
    L=out[ORD.index(k)*H:(ORD.index(k)+1)*H];L[sel,:3]=a[sel,:3];L[sel,3]=(np.clip(al[sel]*1.25,0,1)*255).astype(np.uint8)
    ys,xs=np.nonzero(sel);bx=boxes.setdefault(k,[9999,9999,0,0]);bx[0]=min(bx[0],xs.min()-2);bx[1]=min(bx[1],ys.min()-2);bx[2]=max(bx[2],xs.max()+3);bx[3]=max(bx[3],ys.max()+3)
Image.fromarray(out,'RGBA').save('/home/user/ynschoi.github.io/handrox/art/face_orig.webp',lossless=True,quality=100,method=6)
print(json.dumps({k:[int(v) for v in b] for k,b in boxes.items()}))
bg=Image.new('RGBA',(W,H),(240,200,160,255))
for i in range(4):bg.alpha_composite(Image.fromarray(out[i*H:(i+1)*H],'RGBA'))
d=bg.convert('RGB');from PIL import ImageDraw;dr=ImageDraw.Draw(d)
for k,b in boxes.items():dr.rectangle(b,outline=(255,0,0));dr.text((b[0],b[1]-10),k,fill=(255,0,0))
d.resize((1024,720)).save(S+'/fo2.png')
import os;print(os.path.getsize('/home/user/ynschoi.github.io/handrox/art/face_orig.webp'))
