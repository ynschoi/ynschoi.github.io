#!/bin/bash
# 나의 명산 지도 배포: 버전 올리고(자동 업데이트용) 두 사이트에 같이 올린다.
# 사용: ./bac100-deploy.sh "커밋 메시지"
set -e
cd "$(dirname "$0")"
V=$(date -u +%Y%m%d-%H%M%S)
sed -i "s/^const APPV=\"[^\"]*\";/const APPV=\"$V\";/" BAC100/index.html
echo "{\"v\":\"$V\"}" > BAC100/version.json
grep -q "const APPV=\"$V\"" BAC100/index.html
git add -A BAC100 bac100-deploy.sh && git commit -q -m "$1" && git push -q origin main
N=../my100san.github.io
if [ -d "$N" ]; then (cd "$N" && git pull -q origin main) ; cp BAC100/index.html BAC100/version.json BAC100/og.jpg BAC100/icon-180.png "$N"/; for d in ex fonts ms nk ocr; do [ -d BAC100/$d ] && cp -r BAC100/$d "$N"/; done
  (cd "$N" && git add -A && git -c user.name="ynschoi" -c user.email="youngsuchoi12@gmail.com" commit -q -m "$1" && git push -q origin main); fi
echo "배포 버전 $V"
