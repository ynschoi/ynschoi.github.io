"""출처별 크롤러 모듈. 각 모듈은 SOURCE(dict)와 crawl() -> list[dict]를 제공한다.

이벤트 스키마 (없는 값은 None 또는 생략)
  id        str  출처 내 고유 ID, '<src>-<원본ID>' 형식 (재실행해도 같아야 함)
  src       str  모듈 키 (예: 'ifbbkorea')
  fed       str  연맹 표기 (PCA, NPCA, WNGP, MUSA, ANBC, BOB, NPC, IFBB PRO, NABBA, KBBF, 몬스터짐, ...)
  name      str  대회명 (연맹 접두어 제외해도 되고 포함해도 됨 — 앱은 fed+name으로 표시)
  date      str  'YYYY-MM-DD' 시작일 (필수)
  end       str  'YYYY-MM-DD' 종료일 (하루짜리면 None)
  place     str  장소(체육관 등)
  city      str  도시/지역 (해외는 'Columbus, OH' 등)
  country   str  국내면 'KR', 해외면 ISO 2자리 국가코드 또는 국가명
  fee       str  참가비 표기 그대로 (예: '180,000원')
  deadline  str  'YYYY-MM-DD' 접수 마감일
  divisions list[str]  종목 목록 (예: ['보디빌딩', '클래식피지크', '비키니'])
  qualification str  참가 자격
  proCards  str  프로카드 정보
  host      str  주최
  url       str  원문(상세) 페이지 URL
  regUrl    str  접수 페이지 URL
  tier      str  'national' | 'regional' | 'international'
  major     bool 챔피언십·파이널·프로쇼 등
  closed    bool 원문에 종료/마감 표시가 있으면 True
"""
