/* ═════════ HANDROX 선수 (미리 구운 3D 그림) ═════════
   3D 모델(tools/prerender/assets/hero.glb)을 tools/prerender로 자세·각도별로 미리 찍어 spr/에 넣어 둠.
   게임은 그 그림만 씀 → three.js·WebGL·외부 서버 없이 바로 뜸. 색은 부위 마스크(spr/*_m.png)로 명암째 바꿈.
   예전 이름(H3)과 같은 사용법: H3.show(자세,x,y,옵션) → 손·엉덩이 위치 반환, H3.frame()에서 실제로 그림 */
(function(){
const MAN=window.HERO_MAN,HEIGHT=115,GW=320,GH=170,BASE='spr/';   /* HEIGHT = 모델 1단위가 경기장 몇 px인지 (선수 키 ≈ 113px) */
const ART={bg_ski:'art/bg_ski.jpg',ski_machine:'art/ski_machine.webp',bg_runf:'art/bg_runf.jpg',bg_run:'art/bg_run.jpg',bg_zone:'art/bg_zone.jpg',row_machine:'art/row_machine.webp',row_seat:'art/row_seat.webp',sled:'art/sled.webp',sled_pull:'art/sled_pull.webp',kb:'art/kb.webp'},IM={};
const H3=window.H3;Object.assign(H3,{ok:false,why:'loading'});
const sheets={};let queue=[],colorKey='',prevSpin=0;
const hex=h=>[parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];
function load(){const names=Object.keys(MAN),files=names.flatMap(n=>[MAN[n].c,MAN[n].m]),arts=Object.keys(ART);let done=0;const total=files.length+arts.length;
  const img=f=>new Promise((res,rej)=>{const im=new Image();im.decoding='async';im.onload=()=>{done++;window.onH3Progress&&onH3Progress(done/total);res(im);};im.onerror=()=>rej(Error(f));im.src=f.startsWith('art/')?f:BASE+f;});
  const artP=Promise.all(arts.map(async k=>{IM[k]=await img(ART[k]);}));
  return Promise.all(names.map(async n=>{const m=MAN[n],[c,k]=await Promise.all([img(m.c),img(m.m)]);
    const W=c.width,H=c.height,cv=document.createElement('canvas');cv.width=W;cv.height=H;const x=cv.getContext('2d',{willReadFrequently:true});
    x.drawImage(c,0,0);const base=x.getImageData(0,0,W,H);x.clearRect(0,0,W,H);x.drawImage(k,0,0,W,H);const md=x.getImageData(0,0,W,H).data,cls=new Uint8Array(W*H);
    for(let i=0;i<cls.length;i++)cls[i]=Math.round(md[i*4]/36);x.putImageData(base,0,0);sheets[n]={m,cv,x,base,cls,W,H};})).then(()=>artP);}
/* 고른 색 입히기: 부위별로 원래 밝기 비율을 유지한 채 색만 바꿈. 처음 값(null)은 원본 그대로 */
function recolor(){const cols=window.handroxColors?handroxColors():{},key=JSON.stringify(cols);if(key===colorKey)return;colorKey=key;
  const T=[null,...['skin','hair','top','shorts','band','shoes'].map(k=>cols[k]?hex(cols[k]):null)];
  for(const s of Object.values(sheets)){const d=s.base.data,out=s.x.createImageData(s.W,s.H),o=out.data,ref=s.m.ref;
    for(let i=0,p=0;p<s.cls.length;p++,i+=4){const k=s.cls[p],t=T[k];o[i+3]=d[i+3];
      if(!t){o[i]=d[i];o[i+1]=d[i+1];o[i+2]=d[i+2];continue;}
      const f=Math.min(1.7,(d[i]*.3+d[i+1]*.59+d[i+2]*.11)/(ref[k]||1));o[i]=Math.min(255,t[0]*f);o[i+1]=Math.min(255,t[1]*f);o[i+2]=Math.min(255,t[2]*f);}
    s.x.putImageData(out,0,0);}
  H3.icon();}
const frameOf=(n,pose,o)=>{const N=sheets[n].m.n;if(pose==='run'||pose==='runf'||pose==='push'||pose==='carry')return ((Math.round((o.ph||0)/(Math.PI*2)*N)%N)+N)%N;return Math.round(Math.min(1,Math.max(0,o.k||0))*(N-1));return 0;};
/* 자세 하나 = 그림 한 칸. 원점(x,y) = 발밑, 로잉은 발 관절 */
H3.show=(pose,x,y,o={})=>{if(!H3.ok)return false;const n=sheets[pose]?pose:'run',s=sheets[n],f=frameOf(n,pose,o),u=HEIGHT*(o.z||1),pt=s.m.pts[f];
  const fx=o.fx?-1:1;if(!o.peek)queue.push({s,f,x,y,u,fx});const P=a=>[x+fx*a[0]*u,y-a[1]*u];return {hand:P(pt.hand),handR:pt.handR?P(pt.handR):P(pt.hand),hips:P(pt.hips),head:pt.head?P(pt.head):P(pt.hips)};};
/* 기구 그림·선·손잡이도 같은 대기열에 (경기장 좌표). 선수보다 먼저 부르면 뒤에, 나중에 부르면 앞에 그려짐 */
H3.img=(k,x,y,w,h,fx)=>{if(H3.ok)queue.push({img:IM[k],x,y,w,h,fx});};
H3.line=(x1,y1,x2,y2,w,col)=>{if(H3.ok)queue.push({line:[x1,y1,x2,y2],w,col});};
H3.rect=(x,y,w,h,col,ol)=>{if(H3.ok)queue.push({rect:[x,y,w,h],col,ol});};
H3.shadow=(x,y,w)=>{if(H3.ok)queue.push({shadow:[x,y,w]});};
/* 배경: run(달리기) / zone(운동 구역). off = 지나온 거리(경기장 px) — 반복해서 흘러감 */
let bgReq=null;H3.bg=(kind,off,bob=0,dim=0)=>{bgReq={kind,off,bob,dim};};
let cv3=null,c3=null,sc=1;
function fit(){if(!cv3)return;const w=cv3.offsetWidth||GW,dpr=Math.min(3,window.devicePixelRatio||1),W=Math.round(w*dpr),H=Math.round(W*(window.HV||GH)/GW);
  if(cv3.width!==W||cv3.height!==H){cv3.width=W;cv3.height=H;}sc=W/GW;OFFp=((window.HV||GH)-GH)*sc;}
let OFFp=0;
H3.frame=()=>{if(!H3.ok)return;recolor();fit();c3.setTransform(1,0,0,1,0,0);c3.clearRect(0,0,cv3.width,cv3.height);c3.setTransform(sc,0,0,sc,0,OFFp);c3.imageSmoothingEnabled=true;c3.imageSmoothingQuality='high';
  for(const q of queue){
    if(q.img){if(q.fx){c3.save();c3.translate(q.x+q.w,q.y);c3.scale(-1,1);c3.drawImage(q.img,0,0,q.w,q.h);c3.restore();}else c3.drawImage(q.img,q.x,q.y,q.w,q.h);continue;}
    if(q.shadow){const [x,y,w]=q.shadow;c3.save();c3.filter='blur(1.5px)';c3.fillStyle='rgba(0,0,0,.42)';c3.beginPath();c3.ellipse(x,y,w/2,3.2,0,0,7);c3.fill();c3.restore();continue;}
    if(q.line){c3.strokeStyle=q.col;c3.lineWidth=q.w;c3.lineCap='round';c3.beginPath();c3.moveTo(q.line[0],q.line[1]);c3.lineTo(q.line[2],q.line[3]);c3.stroke();continue;}
    if(q.rect){const [x,y,w,h]=q.rect;c3.fillStyle=q.ol;c3.beginPath();c3.roundRect(x-.6,y-.6,w+1.2,h+1.2,h/2);c3.fill();c3.fillStyle=q.col;c3.beginPath();c3.roundRect(x,y,w,h,h/2);c3.fill();continue;}
    const m=q.s.m,g=q.u/m.ppu;if(q.fx<0){c3.save();c3.translate(q.x,0);c3.scale(-1,1);c3.drawImage(q.s.cv,q.f*m.w,0,m.w,m.h,m.box[0]*q.u,q.y-m.box[3]*q.u,m.w*g,m.h*g);c3.restore();}else c3.drawImage(q.s.cv,q.f*m.w,0,m.w,m.h,q.x+m.box[0]*q.u,q.y-m.box[3]*q.u,m.w*g,m.h*g);}queue=[];
  if(cbg&&bgReq){const im=IM['bg_'+bgReq.kind],w=GW*sc,h=GH*sc,o=((bgReq.off*.7)%GW+GW)%GW*sc;cbg.setTransform(1,0,0,1,0,0);
    if(cvbg.width!==cv3.width||cvbg.height!==cv3.height){cvbg.width=cv3.width;cvbg.height=cv3.height;}cbg.imageSmoothingQuality='high';
    const ih=w*im.height/im.width,iy=OFFp+h-ih;   /* 그림 아래쪽(바닥)을 경기장 170 기준선에 맞추고 위쪽은 남는 만큼 보임 */
    if(bgReq.kind==='runf')runfBg(im,w,ih,iy,bgReq.off,bgReq.bob);else{cbg.drawImage(im,-o,iy,w,ih);cbg.drawImage(im,w-o,iy,w,ih);}
    if(bgReq.dim){const H2=cvbg.height,g=cbg.createRadialGradient(w/2,H2*.62,H2*.15,w/2,H2*.62,w*.62);   /* 기구 종목: 가장자리를 어둡게 해 선수에 시선이 가게 */
      g.addColorStop(0,'rgba(8,8,11,.15)');g.addColorStop(1,'rgba(8,8,11,.72)');cbg.fillStyle=g;cbg.fillRect(0,0,w,H2);}bgReq=null;}
  const pc=document.getElementById('cuPrev3');if(pc&&pc.offsetParent){const s=sheets.turn,N=s.m.n,i=((Math.round(prevSpin/(Math.PI*2)*N)%N)+N)%N,x=pc.getContext('2d');
    x.clearRect(0,0,pc.width,pc.height);const k=Math.min(pc.width/s.m.w,pc.height/s.m.h);x.imageSmoothingQuality='high';x.drawImage(s.cv,i*s.m.w,0,s.m.w,s.m.h,(pc.width-s.m.w*k)/2,(pc.height-s.m.h*k)/2,s.m.w*k,s.m.h*k);}};
H3.icon=()=>{const fc=document.getElementById('face'),s=sheets.icon;if(!fc||!s)return;const x=fc.getContext('2d');x.setTransform(1,0,0,1,0,0);x.clearRect(0,0,fc.width,fc.height);x.imageSmoothingQuality='high';x.drawImage(s.cv,0,0,s.m.w,s.m.h,0,0,fc.width,fc.height);};
H3.colors=()=>window.handroxColors?handroxColors():{};
let cvbg=null,cbg=null;
/* 정면 트랙: 배경은 고정, 바닥 가로줄과 펜스 빛이 소실점 쪽으로 빨려 들어감 (선수가 카메라 쪽으로 달려오니 바닥은 멀어짐).
   off = 지나온 거리(경기장 px). 40px마다 줄 한 칸. bob = 걸음마다 화면 흔들림(px) */
function runfBg(im,w,ih,iy,off,bob){const k=sc,vx=GW/2,vy=635/1024*GW*im.height/im.width-(GW*im.height/im.width-GH),t=1-((off/40)%1+1)%1;cbg.drawImage(im,0,iy-bob*k,w,ih+bob*k);cbg.save();cbg.translate(0,OFFp);cbg.scale(k,k);cbg.translate(0,-bob);
  for(let i=0;i<8;i++){const u=(i+t)/8,y=vy+(GH-vy)*u**2.4,half=(y-vy)*1.9;cbg.strokeStyle=`rgba(200,200,210,${(40+120*u)/255})`;cbg.lineWidth=(1+u*5)/3;cbg.beginPath();cbg.moveTo(vx-half,y);cbg.lineTo(vx+half,y);cbg.stroke();}
  for(let i=0;i<6;i++){const u=(i+t)/6,y=vy+(GH-vy)*.62*u**2.4,x=(y-vy)*3.1;cbg.fillStyle=`rgba(255,230,120,${(60+120*u)/255})`;
    for(const sg of [-1,1]){cbg.beginPath();cbg.ellipse(vx+sg*x,y,(6*u+2)/3,(2*u+1)/3,0,0,7);cbg.fill();}}
  cbg.restore();}
function start(){cv3=document.getElementById('cv3');c3=cv3.getContext('2d');cvbg=document.getElementById('cvbg');cbg=cvbg&&cvbg.getContext('2d');const pc=document.getElementById('cuPrev3');
  if(pc){pc.width=pc.offsetWidth*3||432;pc.height=pc.offsetHeight*3||504;let d=null;pc.addEventListener('pointerdown',e=>{d=e.clientX;try{pc.setPointerCapture(e.pointerId);}catch(_){}});
    pc.addEventListener('pointermove',e=>{if(d==null)return;prevSpin-=(e.clientX-d)*.025;d=e.clientX;});['pointerup','pointercancel'].forEach(v=>pc.addEventListener(v,()=>{d=null;}));}
  load().then(()=>{H3.ok=true;H3.why='ok';document.documentElement.classList.add('has3d');recolor();H3.icon();window.onH3Ready&&onH3Ready();})
    .catch(e=>{H3.why=String(e&&e.message||e);window.onH3Fail&&onH3Fail(H3.why);});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
