#!/bin/bash
# 나의 명산 지도 배포: 버전 올리고(자동 업데이트용) 두 사이트에 같이 올린다.
# 사용: OK=영수확인 ./bac100-deploy.sh "커밋 메시지"   (영수님께 반영 여부를 먼저 물어 "반영" 답을 받은 뒤에만)
set -e
cd "$(dirname "$0")"
# 공개 앱이라 영수님 확인 없이 올리지 않는다. 확인받은 뒤에만 OK=영수확인 을 붙여 실행.
if [ "$OK" != "영수확인" ]; then echo "중단: 영수님 확인 전에는 배포하지 않음 (OK=영수확인 ./bac100-deploy.sh ...)"; exit 1; fi
V=$(date -u +%Y%m%d-%H%M%S)
sed -i "s/^const APPV=\"[^\"]*\";/const APPV=\"$V\";/" BAC100/index.html
echo "{\"v\":\"$V\"}" > BAC100/version.json
grep -q "const APPV=\"$V\"" BAC100/index.html
git add -A BAC100 bac100-deploy.sh && git commit -q -m "$1" && git push -q origin main
N=../my100san.github.io
if [ -d "$N" ]; then (cd "$N" && git pull -q origin main) ; cp BAC100/index.html BAC100/version.json BAC100/og.jpg BAC100/icon-180.png "$N"/; for d in ex fonts ms nk ocr; do [ -d BAC100/$d ] && cp -r BAC100/$d "$N"/; done
  (cd "$N" && git add -A && git -c user.name="ynschoi" -c user.email="youngsuchoi12@gmail.com" commit -q -m "$1" && git push -q origin main); fi
echo "배포 버전 $V"
