// GLB → 텍스처를 뺀 형태 GLB + 텍스처 PNG. 아티팩트는 .glb·data:·blob: 주소를 못 쓰므로 형태는 base64 .txt로도 저장
import {NodeIO} from '@gltf-transform/core';import {prune} from '@gltf-transform/functions';import fs from 'fs';
const io=new NodeIO();const doc=await io.read(process.argv[2]);const t=doc.getRoot().listTextures()[0];fs.writeFileSync(process.argv[3]+'_tex.png',Buffer.from(t.getImage()));
for(const m of doc.getRoot().listMaterials())m.setBaseColorTexture(null);await doc.transform(prune({keepAttributes:true}));
const glb=await io.writeBinary(doc);fs.writeFileSync(process.argv[3]+'.glb',glb);fs.writeFileSync(process.argv[3]+'_geo.txt',Buffer.from(glb).toString('base64'));
console.log('glb',glb.length,'tex',fs.statSync(process.argv[3]+'_tex.png').size);
