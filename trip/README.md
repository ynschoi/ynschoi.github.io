# 나의 도트 여행 지구 (trip)

여행 기록을 도트 지구 위에서 보여주는 페이지. 블록 캐릭터가 여행지 사이를 걷고, 도착하면 그곳 옷으로 갈아입고, ● 버튼으로 사진이 나온다.

## 파일
- `index.html` — 실행 파일. `src/head2.html` + `src/shared.js` + `src/tail2.js` 를 순서대로 이어 붙인 것.
  - 다시 만들기: `cat src/head2.html src/shared.js src/tail2.js > index.html`
- `src/head2.html` — 화면 구성·CSS·**여행지 목록(TRIPS)**. 여행지/날짜/옷/메모/사진은 여기서 고친다.
- `src/shared.js` — 지구(도트 지도·확대 단계·깃발).
- `src/tail2.js` — 캐릭터(블록 인형 `makeCleanDoll`, 옷 `CLEAN_OUTFITS`), 지형, 카메라, 걷기, 사진, 하트, 하늘색.
- `tex/` — 미리 만든 지도 이미지(256~2048)와 높이 이미지 `levels.png`(높이값×16 저장).
- `cards/` — 예전 그림 캐릭터(앞·뒤). 지금은 3D 모델을 못 읽을 때의 대체용.
- `models/char.glb` — 받은 3D 모델(지금은 사용 안 함).

## 사진 넣기
개인 사진은 공개 저장소라 올리지 않았다. `trip/photos/` 에 넣고 `src/head2.html` 의 해당 여행지에
`photos: ["photos/파일.jpg", ...]` 를 추가한 뒤 index.html 을 다시 만든다.

## 참고
- 지형 높이: three-globe 패키지(MIT)의 earth-topology 이미지(NASA 원자료)에서 만듦.
- 하트는 claude.ai 아티팩트의 공유 저장소를 쓸 때만 여러 사람 하트가 합쳐진다. 다른 곳에 올리면 그 기기에만 저장된다.
- three.js 0.147.0 (jsdelivr) 사용.
