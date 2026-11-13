# spr/manifest.json을 index.html 안에 넣음 (manifest 파일을 따로 받으면 캐시 문제가 생겨서)
import json,re,sys
p=sys.argv[1] if len(sys.argv)>1 else 'index.html';s=open(p).read();m=open('spr/manifest.json').read()
s=re.sub(r'/\*HERO_MAN\*/.*?/\*END_HERO_MAN\*/','/*HERO_MAN*/window.HERO_MAN='+m.replace('\\','\\\\')+';/*END_HERO_MAN*/',s,flags=re.S);open(p,'w').write(s);print('manifest',len(m))
# 첫 화면에 바로 필요한 것(배경·정면 달리기 그림·그림 코드)은 페이지 맨 위에서 미리 받기 시작 (페이지 끝까지 읽기 전에)
s=open(p).read();M=json.loads(m);pre=''.join(f'<link rel="preload" href="{u}" as="{a}">' for u,a in [('art/bg_runf.webp','image'),('spr/'+M['runfp' if 'runfp' in M else 'runf']['c'],'image'),('hero_spr.js','script')])
s=re.sub(r'<!--PRELOAD-->.*?<!--/PRELOAD-->','<!--PRELOAD-->'+pre+'<!--/PRELOAD-->',s,flags=re.S);open(p,'w').write(s);print('preload ok')
