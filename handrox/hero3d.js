/* ═════════ HANDROX 3D 선수 (three.js) ═════════
   - hero.glb: Tripo로 만든 통짜 메시(뼈대·모프·파츠 없음, 텍스처 1장). 1.47M→16k 삼각형으로 줄인 것
   - 뼈대: GLB에 skin이 있으면 그걸 쓰고(Mixamo 이름 매핑), 없으면 autoRig()가 몸 위치로 직접 심음
   - 색: hero_mask.png(텍스처 픽셀별 부위 번호)로 피부·머리·상의·반바지·밴드·신발 색을 명암째 바꿈
   - 화면: 2D 경기장 위에 320×170으로 렌더하고 픽셀처럼 확대 → 기존 도트 화면과 같은 해상도
   로드에 실패하거나 WebGL이 없으면 window.H3는 ok=false로 남고, 게임은 기존 2D 캐릭터로 그대로 돎 */
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

const H3={ok:false,why:'loading'};window.H3=H3;
const GW=320,GH=170,HEIGHT=70;          // 경기장 좌표계, 선수 키(경기장 px)

/* ── 뼈대 ── 모델 좌표: 키 1(y -0.5~0.5), 앞 +x, 옆 z. z>0 쪽이 카메라에 가까운 팔·다리 */
const J={root:[0,-.5,0],hips:[.02,-.27,0],spine:[.02,-.16,0],neck:[.02,-.055,0],head:[.02,-.03,0],
  armN:[.01,-.125,.135],foreN:[.01,-.125,.235],handN:[.01,-.125,.335],armF:[.01,-.125,-.135],foreF:[.01,-.125,-.235],handF:[.01,-.125,-.335],
  legN:[.02,-.305,.075],shinN:[.025,-.385,.075],footN:[.03,-.47,.075],legF:[.02,-.305,-.075],shinF:[.025,-.385,-.075],footF:[.03,-.47,-.075]};
const PARENT={hips:'root',spine:'hips',neck:'spine',head:'neck',armN:'spine',foreN:'armN',handN:'foreN',armF:'spine',foreF:'armF',handF:'foreF',
  legN:'hips',shinN:'legN',footN:'shinN',legF:'hips',shinF:'legF',footF:'shinF'};
const ORDER=['root',...Object.keys(PARENT)];
/* Mixamo 등 외부 리그를 받으면 이 이름표로 연결 (아직 실제 리그 GLB로는 시험 못 함) */
const MIXAMO={hips:'Hips',spine:'Spine1',neck:'Neck',head:'Head',armN:'LeftArm',foreN:'LeftForeArm',handN:'LeftHand',armF:'RightArm',foreF:'RightForeArm',handF:'RightHand',
  legN:'LeftUpLeg',shinN:'LeftLeg',footN:'LeftFoot',legF:'RightUpLeg',shinF:'RightLeg',footF:'RightFoot'};

const sm=(a,b,x)=>{const t=Math.min(1,Math.max(0,(x-a)/(b-a)));return t*t*(3-2*t);};
/* 정점마다 어느 뼈를 따라 움직일지(최대 2개 섞기). 이 모델 치수에 맞춘 규칙 — 다른 모델이면 J와 함께 다시 맞춰야 함 */
function weightsFor(x,y,z){const az=Math.abs(z),n=z>=0;
  if(az>.13&&y>-.2&&(y<-.05||(az>.19&&y<.01))){   /* 엄지 끝은 y가 -0.05보다 높이 솟아 있음 */const a=n?'armN':'armF',f=n?'foreN':'foreF';
    if(az<.16)return [['spine',1-sm(.13,.16,az)],[a,sm(.13,.16,az)]];
    return [[a,1-sm(.215,.25,az)],[f,sm(.215,.25,az)]];}
  if(y>-.07)return [['spine',1-sm(-.07,-.035,y)],['head',sm(-.07,-.035,y)]];
  if(y<-.29&&az>.008){const l=n?'legN':'legF',s=n?'shinN':'shinF';
    if(y>-.34)return [['hips',sm(-.34,-.29,y)],[l,1-sm(-.34,-.29,y)]];
    return [[l,sm(-.4,-.365,y)],[s,1-sm(-.4,-.365,y)]];}
  return [['hips',1-sm(-.25,-.19,y)],['spine',sm(-.25,-.19,y)]];}

function autoRig(mesh){const g=mesh.geometry,P=g.attributes.position,n=P.count,si=new Uint16Array(n*4),sw=new Float32Array(n*4);
  for(let i=0;i<n;i++){const w=weightsFor(P.getX(i),P.getY(i),P.getZ(i)).filter(e=>e[1]>1e-4);let s=0;w.forEach(e=>s+=e[1]);
    w.forEach((e,k)=>{si[i*4+k]=ORDER.indexOf(e[0]);sw[i*4+k]=e[1]/s;});}
  g.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(si,4));g.setAttribute('skinWeight',new THREE.Float32BufferAttribute(sw,4));
  const bones={};ORDER.forEach(k=>{const b=new THREE.Bone();b.name=k;bones[k]=b;});
  ORDER.forEach(k=>{const p=J[k],q=PARENT[k]?J[PARENT[k]]:[0,0,0];bones[k].position.set(p[0]-q[0],p[1]-q[1],p[2]-q[2]);if(PARENT[k])bones[PARENT[k]].add(bones[k]);});
  const sk=new THREE.SkinnedMesh(g,mesh.material);sk.add(bones.root);sk.bind(new THREE.Skeleton(ORDER.map(k=>bones[k])));return {mesh:sk,bones};}

/* ── 자세 ── 각 뼈의 '세상 기준' 회전을 정해 주면 부모 회전을 빼서 넣음 */
const qa=(ax,a)=>new THREE.Quaternion().setFromAxisAngle(ax,a),X=new THREE.Vector3(1,0,0),Z=new THREE.Vector3(0,0,1);
function setW(R,k,q){const b=R.bones[k],p=b.parent;p.updateWorldMatrix(true,false);const pq=new THREE.Quaternion();p.getWorldQuaternion(pq);
  const rq=new THREE.Quaternion();R.obj.getWorldQuaternion(rq);b.quaternion.copy(pq.invert().multiply(rq).multiply(q));b.updateMatrixWorld(true);}
/* 팔: down=T자에서 내리는 각, sw=앞뒤 흔들기(+앞), el=팔꿈치 굽힘(+앞으로) / 다리: sw=허벅지(+앞), kn=무릎 굽힘 */
function arm(R,side,down,sw,el){const s=side==='N'?1:-1,d=qa(X,s*down);setW(R,'arm'+side,qa(Z,sw).multiply(d));setW(R,'fore'+side,qa(Z,sw+el).multiply(d));}
function leg(R,side,sw,kn,ft=0){setW(R,'leg'+side,qa(Z,sw));setW(R,'shin'+side,qa(Z,sw-kn));setW(R,'foot'+side,qa(Z,sw-kn+ft));}
const POSES={
  idle(R,o){const b=Math.sin(o.t*2.2);setW(R,'hips',qa(Z,0));setW(R,'spine',qa(Z,-.03*b));setW(R,'neck',qa(Z,0));setW(R,'head',qa(Z,.04*b));
    arm(R,'N',1.25,.05,.15);arm(R,'F',1.25,-.05,.15);leg(R,'N',0,0);leg(R,'F',0,0);return {dy:0};},
  run(R,o){const p=o.ph,s=Math.sin(p),c=Math.cos(p);setW(R,'hips',qa(Z,-.12));setW(R,'spine',qa(Z,-.2));setW(R,'neck',qa(Z,-.2));setW(R,'head',qa(Z,-.05+.04*c));
    leg(R,'N',.75*s,.35+.9*Math.max(0,-c),.2);leg(R,'F',-.75*s,.35+.9*Math.max(0,c),.2);
    arm(R,'N',1.3,-.85*s,1.3);arm(R,'F',1.3,.85*s,1.3);return {dy:Math.abs(c)*.035};}};

/* ── 색 ── 마스크 번호: 1 피부 2 머리 3 상의 4 반바지 5 밴드 6 신발 */
let baseTex=null,maskPx=null,texCv=null,texCtx=null,texture=null,refLum=null,lastColors='';
function prepColors(map,maskImg){const w=map.image.width,h=map.image.height;texCv=document.createElement('canvas');texCv.width=w;texCv.height=h;texCtx=texCv.getContext('2d');
  texCtx.drawImage(map.image,0,0);baseTex=texCtx.getImageData(0,0,w,h);const m=document.createElement('canvas');m.width=w;m.height=h;const mx=m.getContext('2d');mx.drawImage(maskImg,0,0,w,h);
  maskPx=mx.getImageData(0,0,w,h).data;refLum=new Float32Array(8);const cnt=new Float32Array(8),d=baseTex.data;
  for(let i=0;i<d.length;i+=4){const k=maskPx[i];refLum[k]+=d[i]*.3+d[i+1]*.59+d[i+2]*.11;cnt[k]++;}for(let k=0;k<8;k++)refLum[k]=refLum[k]/(cnt[k]||1);
  texture=new THREE.CanvasTexture(texCv);texture.flipY=map.flipY;texture.colorSpace=THREE.SRGBColorSpace;return texture;}
const hex=h=>[parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];
function applyColors(cols){const key=JSON.stringify(cols);if(!texture||key===lastColors)return;lastColors=key;
  const out=texCtx.createImageData(baseTex.width,baseTex.height),d=baseTex.data,o=out.data,T=[null,...['skin','hair','top','shorts','band','shoes'].map(k=>cols[k]?hex(cols[k]):null)];
  for(let i=0;i<d.length;i+=4){const k=maskPx[i],t=T[k];if(!t){o[i]=d[i];o[i+1]=d[i+1];o[i+2]=d[i+2];o[i+3]=255;continue;}
    const f=Math.min(1.6,(d[i]*.3+d[i+1]*.59+d[i+2]*.11)/(refLum[k]||1));o[i]=Math.min(255,t[0]*f);o[i+1]=Math.min(255,t[1]*f);o[i+2]=Math.min(255,t[2]*f);o[i+3]=255;}
  texCtx.putImageData(out,0,0);texture.needsUpdate=true;}

/* ── 장면 ── 경기장 위 레이어(320×170 픽셀) + 캐릭터 만들기 미리보기 */
function makeView(canvas,w,h,ortho){const r=new THREE.WebGLRenderer({canvas,antialias:false,alpha:true,powerPreference:'low-power'});r.setPixelRatio(1);r.setSize(w,h,false);r.outputColorSpace=THREE.SRGBColorSpace;
  const sc=new THREE.Scene();sc.add(new THREE.HemisphereLight(0xffffff,0x40404c,2.4));const d=new THREE.DirectionalLight(0xffffff,1.6);d.position.set(-1,2,3);sc.add(d);
  const cam=ortho?new THREE.OrthographicCamera(0,w,0,-h,-500,500):new THREE.PerspectiveCamera(28,w/h,.1,20);if(!ortho){cam.position.set(0,0,3.2);}
  return {r,sc,cam,w,h};}
function rigged(src){const obj=new THREE.Group();const m=SkeletonUtils.clone(src.mesh);obj.add(m);const bones={};m.skeleton.bones.forEach(b=>bones[b.name]=b);return {obj,mesh:m,bones};}

let RIG=null,stage=null,stageR=null,want=null,cleared=true,prev=null,prevR=null,prevYaw=-1.05,prevSpin=0;
H3.show=(pose,x,y,o={})=>{if(!H3.ok)return false;want={pose,x,y,o};return true;};
H3.frame=t=>{if(!H3.ok)return;applyColors(H3.colors());
  if(want){const R=stageR,w=want;R.obj.visible=true;R.obj.position.set(w.x,-w.y,0);R.obj.scale.setScalar(HEIGHT);R.obj.rotation.y=w.o.yaw??-.55;
    R.obj.updateMatrixWorld(true);const r=POSES[w.pose](R,{t:t/1000,...w.o});R.obj.position.y=-w.y+HEIGHT*.5+r.dy*HEIGHT;stage.r.render(stage.sc,stage.cam);cleared=false;want=null;}
  else if(!cleared){stage.r.clear();cleared=true;}
  const pc=document.getElementById('cuPrev3');if(prev&&pc&&pc.offsetParent){prevR.obj.rotation.y=prevYaw+prevSpin;POSES.idle(prevR,{t:t/1000});prev.r.render(prev.sc,prev.cam);}};
H3.colors=()=>window.handroxColors?window.handroxColors():{};

async function init(){const cv=document.getElementById('cv3');if(!cv)return;
  try{const u=window.HERO_URL||'hero.glb';let g;          /* .txt = base64로 담은 GLB (아티팩트용). 텍스처는 hero_tex.png로 따로 */
    if(u.endsWith('.txt')){const t=(await (await fetch(u)).text()).trim(),bin=Uint8Array.from(atob(t),c=>c.charCodeAt(0));g=await new GLTFLoader().parseAsync(bin.buffer,'');}
    else g=await new GLTFLoader().loadAsync(u);let mesh=null;g.scene.traverse(o=>{if(o.isMesh&&!mesh)mesh=o;});if(!mesh)throw Error('no mesh');
    const img=src=>new Promise((res,rej)=>{const im=new Image();im.onload=()=>res(im);im.onerror=()=>rej(Error('image '+src));im.src=src;});
    const [texImg,mask]=await Promise.all([img('hero_tex.png'),img('hero_mask.png')]);
    const tex=prepColors({image:texImg,flipY:false},mask);mesh.material=new THREE.MeshLambertMaterial({map:tex});
    let src;if(g.scene.getObjectByProperty('type','SkinnedMesh')){H3.why='rigged GLB: 외부 리그 이름 매핑은 아직 미검증';throw Error(H3.why);} else src=autoRig(mesh);
    stage=makeView(cv,GW,GH,true);stageR=rigged(src);stage.sc.add(stageR.obj);
    const pc=document.getElementById('cuPrev3');
    if(pc){prev=makeView(pc,192,224,false);prevR=rigged(src);prevR.obj.position.y=0;prevR.obj.scale.setScalar(.95);prev.sc.add(prevR.obj);
      let d=null;pc.addEventListener('pointerdown',e=>{d=e.clientX;try{pc.setPointerCapture(e.pointerId);}catch(_){}});pc.addEventListener('pointermove',e=>{if(d==null)return;prevSpin+=(e.clientX-d)*.02;d=e.clientX;});
      ['pointerup','pointercancel'].forEach(v=>pc.addEventListener(v,()=>{d=null;}));}
    H3.ok=true;H3.why='ok';document.documentElement.classList.add('has3d');}
  catch(e){H3.ok=false;H3.why=String(e&&e.message||e);console.warn('HANDROX 3D off:',H3.why);}}
init();
