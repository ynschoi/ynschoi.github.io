// 홈 화면 설치(갤럭시·크롬)용 최소 서비스 워커 — 아무것도 저장하지 않고 그대로 인터넷에서 받음(업데이트 지연 없음)
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
