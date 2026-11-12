/* HANDROX 선수 뼈대·자세 (빌드 전용). prerender.html이 이걸로 3D 모델을 움직여 프레임을 구움.
   게임 실행 중에는 three.js를 쓰지 않음 — 구운 그림만 씀 */
import * as THREE from 'three';
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
    arm(R,'N',1.3,-.85*s,1.3);arm(R,'F',1.3,.85*s,1.3);return {dy:Math.abs(c)*.035};},
  /* 로잉: k 0=캐치(무릎 접고 앞으로) → 1=피니시(다리 펴고 뒤로 젖히고 손잡이를 가슴으로).
     당길 때 다리→허리→팔 순서, 돌아올 때 팔→허리→다리 순서가 k 하나로 저절로 됨. 발은 발판에 고정(anchor) */
  row(R,o){const k=Math.min(1,Math.max(0,o.k||0)),L=sm(0,.55,k),B=sm(.25,.75,k),A=sm(.55,1,k),lr=(a,b,t)=>a+(b-a)*t,lean=lr(-.8,.6,B);
    setW(R,'hips',qa(Z,lean*.5));setW(R,'spine',qa(Z,lean));setW(R,'neck',qa(Z,lean*.6));setW(R,'head',qa(Z,lean*.35));
    const a1=lr(2.3,1.55,L),a2=lr(.35,1.5,L);leg(R,'N',a1,a1-a2,-.6);leg(R,'F',a1,a1-a2,-.6);
    const sw=lr(1.55,-.2,A),el=lr(-.1,1.75,A);arm(R,'N',1.3,sw,el);arm(R,'F',1.3,sw,el);return {anchor:'footN'};}};
const _v=new THREE.Vector3();
function wpos(R,k){R.bones[k].getWorldPosition(_v);return [_v.x,-_v.y];}


export {J,ORDER,autoRig,POSES,wpos,sm};
