# 구운 프레임 → 종목별 가로 띠 그림(색: webp, 부위: png) + manifest. 파일 이름에 내용 해시를 붙여 캐시 문제를 없앰
# 사용: python3 pack.py <bake폴더> <handrox/spr>
import sys,json,hashlib,os,glob
import numpy as np
from PIL import Image
src,dst=sys.argv[1],sys.argv[2];os.makedirs(dst,exist_ok=True)
for f in glob.glob(dst+'/*'):os.remove(f)
meta=json.load(open(src+'/meta.json'));man={}
for name,m in meta.items():
    n=len(m['frames']);W,H=m['w'],m['h'];C=np.zeros((H,W*n,4),np.uint8);M=np.zeros((H,W*n),np.uint8)
    for i in range(n):
        c=np.array(Image.open(f'{src}/{name}_{i}_c.png').convert('RGBA'));mk=np.array(Image.open(f'{src}/{name}_{i}_m.png').convert('RGBA').resize((c.shape[1],c.shape[0]),Image.NEAREST))
        k=np.round(mk[...,0]/36).astype(np.uint8);k[mk[...,3]<128]=0
        # 부위 경계의 흐려진(안티에일리어싱) 값 정리: 두 부위 사이 값이 엉뚱한 부위 번호가 되는 것(예: 피부1·상의3 사이 = 머리2)을 옆 부위로 바꿈
        v=mk[...,0].astype(int);bad=np.abs(v-k.astype(int)*36)>5
        for ax in (1,0):
            a_=np.roll(k,1,ax).astype(int);b_=np.roll(k,-1,ax).astype(int);ki=k.astype(int)
            mid=(a_!=ki)&(b_!=ki)&(np.minimum(a_,b_)<ki)&(ki<np.maximum(a_,b_));bad|=mid
        for _ in range(2):
            for dy,dx in ((0,1),(0,-1),(1,0),(-1,0)):
                sh=np.roll(np.roll(k,dy,0),dx,1);shb=np.roll(np.roll(bad,dy,0),dx,1);f_=bad&~shb;k[f_]=sh[f_];bad&=~f_
        for _ in range(3):                                   # 가장자리(색은 있는데 부위가 비어 있는 픽셀)를 옆 부위로 채움
            z=(k==0)&(c[...,3]>0)&(mk[...,3]<250)   # 테두리만 (눈·입처럼 일부러 비워 둔 안쪽 칸은 그대로 둠)
            for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                sh=np.roll(np.roll(k,dy,0),dx,1);fill=z&(k==0)&(sh>0);k[fill]=sh[fill]
        C[:,i*W:(i+1)*W]=c;M[:,i*W:(i+1)*W]=k
    rgb=C[...,:3].astype(float);lum=rgb[...,0]*.3+rgb[...,1]*.59+rgb[...,2]*.11;ok=C[...,3]>200
    ref=[float(lum[ok&(M==k)].mean()) if (ok&(M==k)).any() else 1.0 for k in range(7)]
    ci=Image.fromarray(C,'RGBA');mi=Image.fromarray(M*36,'L')
    tmpc=f'{dst}/_c.webp';ci.save(tmpc,'WEBP',quality=90,method=6);tmpm=f'{dst}/_m.png';mi.save(tmpm,optimize=True)
    todo=[(tmpc,'c','webp'),(tmpm,'m','png')]
    if os.path.exists(f'{src}/{name}_0_f.png'):              # 그림 자리 지도(머리통 선수): 절반 크기로 줄여 한 띠로
        Fh,Fw=H//2,W//2;F=np.zeros((Fh,Fw*n,4),np.uint8)
        for i in range(n):F[:,i*Fw:(i+1)*Fw]=np.array(Image.open(f'{src}/{name}_{i}_f.png').convert('RGBA').resize((Fw,Fh),Image.NEAREST))
        F[F[...,3]<128]=0;F[...,3]=np.where(F[...,3]>=128,255,0);tmpf=f'{dst}/_f.png';Image.fromarray(F,'RGBA').save(tmpf,optimize=True);todo.append((tmpf,'f','png'))
    out={}
    for tmp,key,ext in todo:
        h=hashlib.sha1(open(tmp,'rb').read()).hexdigest()[:8];fn=f'{name}_{key}_{h}.{ext}';os.rename(tmp,f'{dst}/{fn}');out[key]=fn
    man[name]={**out,'n':n,'w':W,'h':H,'box':m['box'],'ppu':m['ppu'],'ref':[round(v,1) for v in ref],'pts':m['frames']}
    print(name,n,'frames',W,'x',H,{k:os.path.getsize(f'{dst}/{v}')//1024 for k,v in out.items()},'KB')
json.dump(man,open(f'{dst}/manifest.json','w'),separators=(',',':'))
