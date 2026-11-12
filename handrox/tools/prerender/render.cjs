// 사용: node render.cjs <출력폴더>   (handrox 폴더를 http로 열고 three는 node_modules에서)
const {chromium}=require('playwright');const http=require('http'),fs=require('fs'),path=require('path');
const ROOT=path.resolve(__dirname,'../..'),THREE=process.env.THREE_DIR,OUT=process.argv[2];fs.mkdirSync(OUT,{recursive:true});
const srv=http.createServer((q,s)=>{let u=decodeURIComponent(q.url.split('?')[0]),f=u.startsWith('/three/')?path.join(THREE,u.slice(7)):path.join(ROOT,u);
  fs.readFile(f,(e,d)=>{if(e){s.writeHead(404);return s.end();}s.writeHead(200,{'content-type':f.endsWith('.js')||f.endsWith('.mjs')?'application/javascript':f.endsWith('.html')?'text/html':'application/octet-stream'});s.end(d);});}).listen(8790);
const TAU=Math.PI*2;
const JOBS={
  run:[...Array(12)].map((_,i)=>({pose:'run',o:{ph:i/12*TAU},yaw:-.55,box:[-.6,.6,-.04,1.1],ppu:260})),
  row:[...Array(11)].map((_,i)=>({pose:'row',o:{k:i/10},yaw:-.12,box:[-.7,.4,-.12,.95],ppu:260})),
  turn:[...Array(12)].map((_,i)=>({pose:'idle',o:{},yaw:-1.05+i*TAU/12,box:[-.46,.46,-.03,1.06],ppu:420})),
  icon:[{pose:'idle',o:{},yaw:-1.3,box:[-.32,.32,.42,1.06],ppu:300}]};
(async()=>{const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const p=await b.newPage();
  p.on('pageerror',e=>console.log('ERR',e.message));await p.goto('http://localhost:8790/tools/prerender/prerender.html');await p.waitForFunction(()=>window.READY,null,{timeout:120000});
  const meta={};for(const [name,jobs] of Object.entries(JOBS)){meta[name]={frames:[]};
    for(let i=0;i<jobs.length;i++){const r=await p.evaluate(j=>window.bake(j),jobs[i]);
      for(const k of ['c','m'])fs.writeFileSync(path.join(OUT,`${name}_${i}_${k}.png`),Buffer.from(r[k].split(',')[1],'base64'));
      meta[name].frames.push(r.pts);meta[name].w=r.w;meta[name].h=r.h;meta[name].box=jobs[i].box;meta[name].ppu=jobs[i].ppu;}console.log(name,jobs.length);}
  fs.writeFileSync(path.join(OUT,'meta.json'),JSON.stringify(meta));await b.close();srv.close();})();
