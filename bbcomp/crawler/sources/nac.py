"""NAC KOREA (www.nackorea.com, cafe24 쇼핑몰형) — 대회 접수를 '상품'으로 판매한다.

사이트 텍스트에는 대회 날짜·장소가 거의 없다(포스터 이미지·인스타그램으로만 공지). 그래서
  1) 허용된 공개 페이지(홈, 대회 소개, 대회접수 상품목록, 공지 게시판 글)의 텍스트에서
     'YYYY년 M월 D일' / 'YYYY.MM.DD' 등 대회 날짜를 찾고,
  2) 상품목록(대회접수, cate_no=28)에서 종목, 상품 상세에서 참가비를 읽는다.
날짜를 찾지 못하면 [] (crawl.py가 기존 데이터를 유지).
robots.txt: /api, /exec/front/, /member/, /myshop/, /protected/, '*board*page=' 등은 쓰지 않는다.
"""
import re
import urllib.robotparser

from .common import UA, get, iso, log, parse_kdate, text

SOURCE = {"key": "nac", "label": "NAC KOREA", "url": "https://www.nackorea.com/"}
BASE = "https://www.nackorea.com"
LIST = BASE + "/product/list.html?cate_no=28"      # 대회접수 (남자/여자 종목)
NOTICE = BASE + "/board/free/list.html?board_no=1"  # 공지사항
# 고정 안내글(규정·환불 등) — 대회 일정 글이 아님
FIXED_NOTICES = {"33", "35", "36", "37", "39", "40", "75"}

_rp = None


def _robots_ok(url):
    global _rp
    if _rp is None:
        _rp = urllib.robotparser.RobotFileParser()
        try:
            _rp.parse(get(BASE + "/robots.txt").splitlines())
        except Exception as e:  # noqa: BLE001
            log(f"  [nac] robots.txt 읽기 실패({e}) — 허용으로 간주")
            _rp.parse([])
    # robotparser는 '*' 와일드카드를 모르므로 직접 확인
    path = url.replace(BASE, "")
    for pat in (r"board.*page=", r"article.*page=", r"board.*category_no=", r"page_[46]="):
        if re.search(pat, path):
            return False
    return _rp.can_fetch(UA, url)


def _get(url):
    if not _robots_ok(url):
        log(f"  [nac] robots.txt 비허용 — 건너뜀: {url}")
        return ""
    return get(url)


def _lines(html):
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html or "")
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    return [l.strip() for l in text(re.sub(r"<[^>]+>", "\n", html)).split("\n") if l.strip()]


DATE_RE = re.compile(r"(20\d{2})\s*(?:년|[./-])\s*(\d{1,2})\s*(?:월|[./-])\s*(\d{1,2})\s*일?")
EVENT_KW = re.compile(r"대회|챔피언|선발전|일시|개최|일정")
VENUE_RE = re.compile(r"(?:장소|대회장|개최지)\s*[:：]?\s*([^\n|]{2,40})")


def _find_events(pages):
    """[(url, lines)] → [{date, end, name, place, url}] — 대회 키워드가 붙은 날짜만."""
    found = {}
    for url, L in pages:
        for i, l in enumerate(L):
            if not DATE_RE.search(l):
                continue
            ctx = " ".join(L[max(0, i - 2):i + 3])
            if not EVENT_KW.search(ctx) or re.search(r"작성일|등록일|조회", ctx):
                continue
            start, end = parse_kdate(l)
            if not start or start[:4] < "2025":
                continue
            ev = found.setdefault(start, {"date": start, "end": end, "url": url})
            if not ev.get("name"):
                for c in L[max(0, i - 3):i + 1][::-1]:
                    if re.search(r"챔피언|선발전|대회", c) and not DATE_RE.search(c) and len(c) <= 60:
                        ev["name"] = c.strip(" :-·[]")
                        break
            v = VENUE_RE.search("\n".join(L[max(0, i - 3):i + 5]))
            if v and not ev.get("place"):
                ev["place"] = v.group(1).strip()
    return list(found.values())


def _products():
    html = _get(LIST)
    prods = []
    for m in re.finditer(r'id="anchorBoxId_(\d+)".*?alt="([^"]+)"', html, re.S):
        pid, alt = m.groups()
        if pid not in [p for p, _ in prods]:
            prods.append((pid, alt))
    return prods, html


def _division(name):
    n = re.sub(r"\[[^\]]*\]", "", name).strip()
    return n or None


def crawl():
    if not _robots_ok(BASE + "/"):
        log("  [nac] robots.txt가 사이트 접근을 허용하지 않음 — 건너뜀")
        return []
    pages = []
    for url in (BASE + "/", BASE + "/page/contest.html"):
        try:
            pages.append((url, _lines(_get(url))))
        except Exception as e:  # noqa: BLE001
            log(f"  [nac] {url} 실패: {e}")

    prods, list_html = _products()
    pages.append((LIST, _lines(list_html)))
    divisions = []
    for _, alt in prods:
        d = _division(alt)
        if d and d not in divisions:
            divisions.append(d)

    # 공지 게시판: 고정 안내글 외의 새 글만 읽는다
    try:
        nl = _get(NOTICE)
        for no in dict.fromkeys(re.findall(r"read\.html\?no=(\d+)&(?:amp;)?board_no=1", nl)):
            if no in FIXED_NOTICES:
                continue
            u = f"{BASE}/board/free/read.html?no={no}&board_no=1"
            pages.append((u, _lines(_get(u))))
    except Exception as e:  # noqa: BLE001
        log(f"  [nac] 공지사항 실패: {e}")

    events = _find_events(pages)
    if not events:
        log("  [nac] 사이트 텍스트에서 대회 날짜를 찾지 못함 (포스터 이미지로만 공지) — 0건")
        return []

    fee = None
    if prods:
        try:
            ph = _get(f"{BASE}/product/detail.html?product_no={prods[0][0]}")
            prices = sorted({int(p.replace(",", "")) for p in
                             re.findall(r'title="판매가"><strong[^>]*>([\d,]+)원', ph)} - {0})
            if prices:
                fee = f"{prices[-1]:,}원"
                if len(prices) > 1:
                    fee += f" (중복출전 {prices[0]:,}원)"
                if any("얼리버드" in a for _, a in prods):
                    fee = "얼리버드 " + fee
        except Exception as e:  # noqa: BLE001
            log(f"  [nac] 참가비 실패: {e}")

    out = []
    for ev in sorted(events, key=lambda e: e["date"]):
        name = ev.get("name") or "NAC코리아 챔피언쉽"
        out.append({
            "id": f"nac-{ev['date']}",
            "fed": "NAC",
            "name": name,
            "date": ev["date"],
            "end": ev.get("end"),
            "place": ev.get("place"),
            "country": "KR",
            "fee": fee,
            "divisions": divisions,
            "qualification": "각 종목 3위 이내 입상 시 NAC 세계선수권(독일) 출전 자격",
            "host": "사단법인 NAC KOREA",
            "url": ev["url"],
            "regUrl": LIST,
            "tier": "national",
            "major": bool(re.search(r"챔피언|선발전|국제", name)),
        })
    return out
