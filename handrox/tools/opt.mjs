// 44MB Tripo GLB → 모바일 웹용. 정점 용접 → 메시 단순화(목표 삼각형 수) → 텍스처 축소 → 법선맵/ORM 제거(픽셀 렌더에선 안 보임)
import {NodeIO} from '@gltf-transform/core';
import {weld,simplify,dedup,prune,textureCompress} from '@gltf-transform/functions';
import {MeshoptSimplifier} from 'meshoptimizer';
import sharp from 'sharp';
const [,,src,dst,tris='16000',tex='512']=process.argv;
const io=new NodeIO();const doc=await io.read(src);
const before=doc.getRoot().listMeshes()[0].listPrimitives()[0].getIndices().getCount()/3;
await MeshoptSimplifier.ready;
const ratio=Math.min(1,+tris/before);
await doc.transform(weld({tolerance:0.0005}),simplify({simplifier:MeshoptSimplifier,ratio,error:0.01,lockBorder:false}));
for(const m of doc.getRoot().listMaterials()){const n=m.getNormalTexture(),o=m.getMetallicRoughnessTexture();m.setNormalTexture(null);m.setMetallicRoughnessTexture(null);m.setMetallicFactor(0);m.setRoughnessFactor(1);}
await doc.transform(prune(),dedup(),textureCompress({encoder:sharp,targetFormat:'png',resize:[+tex,+tex]}));
const p=doc.getRoot().listMeshes()[0].listPrimitives()[0];
console.log('tris',before,'->',p.getIndices().getCount()/3,'verts',p.getAttribute('POSITION').getCount());
await io.write(dst,doc);
