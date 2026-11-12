// 사용: node render.cjs <출력폴더>   (handrox 폴더를 http로 열고 three는 node_modules에서)
const {chromium}=require('playwright');const http=require('http'),fs=require('fs'),path=require('path');
const ROOT=path.resolve(__dirname,'../..'),PAGE=process.env.PAGE||'prerender.html',THREE=process.env.THREE_DIR,OUT=process.argv[2];fs.mkdirSync(OUT,{recursive:true});
const srv=http.createServer((q,s)=>{let u=decodeURIComponent(q.url.split('?')[0]),f=u.startsWith('/three/')?path.join(THREE,u.slice(7)):path.join(ROOT,u);
  fs.readFile(f,(e,d)=>{if(e){s.writeHead(404);return s.end();}s.writeHead(200,{'content-type':f.endsWith('.js')||f.endsWith('.mjs')?'application/javascript':f.endsWith('.html')?'text/html':'application/octet-stream'});s.end(d);});}).listen(8790);
const TAU=Math.PI*2;
const JOBS=process.env.ONLY==='lw'?{lunge:[...Array(11)].map((_,i)=>({pose:'lunge',o:{k:i/10,lead:'Left'},yaw:0,box:[-.6,.6,-.02,1.07],ppu:300})),lunge2:[...Array(11)].map((_,i)=>({pose:'lunge',o:{k:i/10,lead:'Right'},yaw:0,box:[-.6,.6,-.02,1.07],ppu:300})),wall:[...Array(11)].map((_,i)=>({pose:'wall',o:{k:i/10},yaw:Math.PI/2-.6,box:[-.55,.55,-.02,1.36],ppu:300}))}   /* 월볼: 스키처럼 오른쪽 사선 뒷모습 */:process.env.ONLY==='carry'?{carry:[...Array(12)].map((_,i)=>({pose:'carry',o:{ph:i/12*TAU},yaw:0,box:[-.44,.44,-.02,1.07],ppu:300}))}:process.env.ONLY==='bbj'?{bbj:[...Array(11)].map((_,i)=>({pose:'bbj',o:{k:i/10},yaw:0,box:[-.5,1.0,-.02,1.0],ppu:300})),bbjj:[...Array(11)].map((_,i)=>({pose:'bbjj',o:{k:i/10},yaw:0,box:[-.5,.6,-.02,1.0],ppu:300}))}:process.env.ONLY==='pull'?{pull:[...Array(11)].map((_,i)=>({pose:'pull',o:{k:i/10},yaw:0,box:[-.55,.6,-.02,1.02],ppu:300}))}:process.env.ONLY==='push'?{push:[...Array(12)].map((_,i)=>({pose:'push',o:{ph:i/12*TAU},yaw:0,box:[-.5,.7,-.02,1.0],ppu:300}))}:process.env.ONLY==='skib'?{skib:[...Array(11)].map((_,i)=>({pose:'skib',o:{k:i/10},yaw:Math.PI/2+(+process.env.YAW||0),box:[-.6,.6,-.02,1.32],ppu:300}))}:process.env.ONLY==='runf'?{runf:[...Array(12)].map((_,i)=>({pose:'runf',o:{ph:i/12*TAU},yaw:-Math.PI/2,box:[-.5,.5,-.04,1.12],ppu:300,persp:2.2}))}:process.env.PAGE==='prerender2.html'?{
  skib:[...Array(11)].map((_,i)=>({pose:'skib',o:{k:i/10},yaw:Math.PI/2-.6,box:[-.62,.62,-.02,1.32],ppu:300})),   /* 스키: 오른쪽 사선 뒷모습 */
  runf:[...Array(12)].map((_,i)=>({pose:'runf',o:{ph:i/12*TAU},yaw:-Math.PI/2,box:[-.5,.5,-.04,1.12],ppu:300,persp:2.2})),
  carry:[...Array(12)].map((_,i)=>({pose:'carry',o:{ph:i/12*TAU},yaw:0,box:[-.44,.44,-.02,1.07],ppu:300})),
  pull:[...Array(11)].map((_,i)=>({pose:'pull',o:{k:i/10},yaw:0,box:[-.55,.6,-.02,1.02],ppu:300})),
  bbj:[...Array(11)].map((_,i)=>({pose:'bbj',o:{k:i/10},yaw:0,box:[-.5,1.0,-.02,1.0],ppu:300})),
  bbjj:[...Array(11)].map((_,i)=>({pose:'bbjj',o:{k:i/10},yaw:0,box:[-.5,.6,-.02,1.0],ppu:300})),
  push:[...Array(12)].map((_,i)=>({pose:'push',o:{ph:i/12*TAU},yaw:0,box:[-.5,.7,-.02,1.0],ppu:300})),   /* 슬레드 푸시: 옆모습 */
  run:[...Array(12)].map((_,i)=>({pose:'run',o:{ph:i/12*TAU},yaw:0,box:[-.44,.44,-.02,1.07],ppu:300})),
  row:[...Array(11)].map((_,i)=>({pose:'row',o:{k:i/10},yaw:0,box:[-.72,.44,-.38,.86],ppu:300})),
  turn:[...Array(12)].map((_,i)=>({pose:'idle',yaw:-Math.PI/2+i*TAU/12,box:[-.34,.34,-.02,1.02],ppu:420})),
  icon:[{pose:'idle',yaw:-Math.PI/2,box:[-.33,.33,.42,1.04],ppu:300}]}:{
  run:[...Array(12)].map((_,i)=>({pose:'run',o:{ph:i/12*TAU},yaw:-.55,box:[-.6,.6,-.04,1.1],ppu:260})),
  row:[...Array(11)].map((_,i)=>({pose:'row',o:{k:i/10},yaw:-.12,box:[-.7,.4,-.12,.95],ppu:260})),
  turn:[...Array(12)].map((_,i)=>({pose:'idle',o:{},yaw:-1.05+i*TAU/12,box:[-.46,.46,-.03,1.06],ppu:420})),
  icon:[{pose:'idle',o:{},yaw:-1.3,box:[-.32,.32,.42,1.06],ppu:300}]};
(async()=>{const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const p=await b.newPage();
  p.on('pageerror',e=>console.log('ERR',e.message));await p.goto('http://localhost:8790/tools/prerender/'+PAGE);await p.waitForFunction(()=>window.READY,null,{timeout:120000});
  const meta={};for(const [name,jobs] of Object.entries(JOBS)){meta[name]={frames:[]};
    for(let i=0;i<jobs.length;i++){const r=await p.evaluate(j=>window.bake(j),jobs[i]);if(r.pts&&!r.pts.hand.length)throw 0;
      for(const k of ['c','m'])fs.writeFileSync(path.join(OUT,`${name}_${i}_${k}.png`),Buffer.from(r[k].split(',')[1],'base64'));
      meta[name].frames.push(r.pts);meta[name].w=r.w;meta[name].h=r.h;meta[name].box=jobs[i].box;meta[name].ppu=jobs[i].ppu;}console.log(name,jobs.length);}
  fs.writeFileSync(path.join(OUT,'meta.json'),JSON.stringify(meta));await b.close();srv.close();})();
