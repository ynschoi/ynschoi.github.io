# spr/manifest.json을 index.html 안에 넣음 (manifest 파일을 따로 받으면 캐시 문제가 생겨서)
import json,re,sys
p=sys.argv[1] if len(sys.argv)>1 else 'index.html';s=open(p).read();m=open('spr/manifest.json').read()
s=re.sub(r'/\*HERO_MAN\*/.*?/\*END_HERO_MAN\*/','/*HERO_MAN*/window.HERO_MAN='+m.replace('\\','\\\\')+';/*END_HERO_MAN*/',s,flags=re.S);open(p,'w').write(s);print('manifest',len(m))
