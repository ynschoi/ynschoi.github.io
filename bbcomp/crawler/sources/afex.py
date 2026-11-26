"""AFEX KOREA — https://www.afex.co.kr/ (imweb 기반 자체 사이트)

출처 세 가지를 합친다 (robots.txt가 막는 /api/·/cms/·/admin/ 은 쓰지 않는다).
  1) /process/api/get_rally_data — 사이트의 '대회 참가 신청' 팝업이 쓰는 JSON.
     기본 호출은 접수 중인 대회만, ?overproduct=1 은 최근 대회(마감 포함)를 준다.
     대회일·장소·접수기간(마감)·종목(category_name)·참가비(option_price)가 있다.
  2) 뉴스룸(/27) 게시글 본문 — '2026 AFEX 시즌 안내'(일시/장소 목록),
     '아이언 클래식 개최 안내'([대회일자]/[대회장소]) 같은 공지.
  3) SEASON_A — 시즌 A(알파 챔피언십·노비스 A·프로퀄 서울)는 공지 본문이 이미지뿐이라
     텍스트로 확인되지 않는다. 보고된 일정을 보조값으로 넣되, 위 출처에서 같은 대회가
     나오면 그 값이 우선한다. USE_SEASON_A=False 로 끌 수 있다.
"""
import json
import re

from .common import get, log, parse_kdate, text, this_year

BASE = "https://www.afex.co.kr"
SOURCE = {"key": "afex", "label": "AFEX KOREA", "url": BASE + "/"}
NEWS = BASE + "/27"
RALLY_API = BASE + "/process/api/get_rally_data"
USE_SEASON_A = True

# (키, 정규식, 표시명, major)
KINDS = [
    ("alpha", r"ALPHA|알파", "알파 챔피언십", True),
    ("omega", r"OMEGA|오메가", "오메가 파이널", True),
    ("pq-busan", r"(?:PRO\s*QUALIFIER|프로\s*퀄리파이어|PQB).*(?:BUSAN|부산)|(?:BUSAN|부산).*(?:PRO\s*QUALIFIER|프로\s*퀄리파이어)",
     "프로 퀄리파이어 부산", False),
    ("pq-seoul", r"(?:PRO\s*QUALIFIER|프로\s*퀄리파이어|PQS).*(?:SEOUL|서울)|(?:SEOUL|서울).*(?:PRO\s*QUALIFIER|프로\s*퀄리파이어)",
     "프로 퀄리파이어 서울", False),
    ("novice-b", r"NOVICE\s*CLASSIC\s*B|노비스\s*클래식\s*B", "노비스 클래식 B", False),
    ("novice-a", r"NOVICE\s*CLASSIC(?:\s*A)?\b|노비스\s*클래식(?:\s*A)?", "노비스 클래식 A", False),
    ("iron", r"IRON\s*CLASSIC|아이언\s*클래식", "아이언 클래식", False),
]

# 사이트 텍스트로 확인되지 않는 시즌 A 보조값 (시즌 안내 공지 이미지 기준으로 보고된 일정)
SEASON_A = [
    ("alpha", "2026-04-25", "2026-04-26"),
    ("novice-a", "2026-05-23", None),
    ("pq-seoul", "2026-06-27", None),
]


def _kind(name):
    for key, pat, label, major in KINDS:
        if re.search(pat, name or "", re.I):
            return key, label, major
    return None


def _city(place):
    m = re.match(r"\s*(서울|부산|대구|인천|광주|대전|울산|강릉|제주|수원|정선)", place or "")
    if m:
        return m.group(1)
    if re.search(r"스위스\s*그랜드", place or ""):
        return "서울"
    return None


def _line(s, label):
    m = re.search(label + r"\s*[:：]\s*([^\r\n]+)", s or "")
    return m.group(1).strip() if m else None


def _rallies():
    """접수 팝업 JSON. 기본 + overproduct 결과를 idx로 합친다."""
    out, viewers = {}, {}
    for q in ("", "?overproduct=1"):
        try:
            d = json.loads(get(RALLY_API + q)).get("data") or {}
        except Exception as e:  # noqa: BLE001
            log(f"  ! afex rally{q} 실패: {e}")
            continue
        for r in d.get("rallies") or []:
            out[r["idx"]] = r
        for v in d.get("viewers") or []:
            viewers[v["idx"]] = v
    return list(out.values()), list(viewers.values())


def _news_posts():
    """뉴스룸 게시글 (제목, 작성일, 본문텍스트). 목록 페이지에 본문이 함께 렌더링된다."""
    posts, seen = [], set()
    for page in range(1, 6):
        try:
            body = get(NEWS, {"page": page})
        except Exception as e:  # noqa: BLE001
            log(f"  ! afex 뉴스룸 p{page} 실패: {e}")
            break
        found = 0
        for m in re.finditer(r"openBoardPopup\((\d+)\)", body):
            pid = m.group(1)
            if pid in seen:
                continue
            seen.add(pid)
            found += 1
            end = body.find("</li>", m.end())
            blk = body[m.end():end if end > 0 else None]
            t = re.search(r"gallery__overlay_title'>(.*?)</div>", blk, re.S)
            dt = re.search(r"overlay_date'>(.*?)</div>", blk, re.S)
            posts.append((pid, text(t.group(1)) if t else "", text(dt.group(1)) if dt else "", text(blk)))
        if not found:
            break
    return posts


def _from_posts(posts, year):
    """공지 본문에서 (이름, 일시, 장소) 추출."""
    out = []
    for pid, title, _, body in posts:
        # 'N. AFEX OMEGA FINAL\n일시: ...\n장소: ...'
        for m in re.finditer(r"(?m)^\s*\d+\.\s*([^\n]+)\n\s*일시\s*[:：]\s*([^\n]+)\n\s*장소\s*[:：]\s*([^\n]+)", body):
            out.append((m.group(1).strip(), m.group(2), m.group(3).strip(), pid))
        # '[대회일자]\n2026년 8월 29일 ...\n[대회장소]\n강릉 ...'
        m1 = re.search(r"\[대회일자\]\s*\n\s*([^\n]+)", body)
        m2 = re.search(r"\[대회장소\]\s*\n\s*([^\n]+)", body)
        if m1 and _kind(title):
            out.append((title, m1.group(1), m2.group(1).strip() if m2 else None, pid))
    res = []
    for name, when, place, pid in out:
        start, end = parse_kdate(when, year)
        if start and start.startswith(str(year)):
            res.append((name, start, end, place, pid))
    return res


def _fee(opts):
    prices = sorted({int(o["option_price"]) for o in opts if str(o.get("option_price") or "").isdigit()
                     and int(o["option_price"]) > 0})
    if not prices:
        return None
    f = lambda p: f"{p:,}원"  # noqa: E731
    return f(prices[0]) if len(prices) == 1 else f"{f(prices[0])}~{f(prices[-1])}"


def _divisions(opts):
    out = []
    for o in opts:
        n = (o.get("category_name") or "").strip()
        if n and n not in out:
            out.append(n)
    return out


def crawl():
    year = this_year()
    ev = {}

    def slot(key, label, major):
        return ev.setdefault(key, {
            "id": f"afex-{year}-{key}", "src": "afex", "fed": "AFEX", "name": label,
            "date": None, "end": None, "place": None, "city": None, "country": "KR",
            "fee": None, "deadline": None, "divisions": [], "host": "AFEX KOREA",
            "url": SOURCE["url"], "regUrl": None, "tier": "national", "major": major,
        })

    rallies, viewers = _rallies()
    for r in rallies:
        k = _kind(r.get("title"))
        start, end = parse_kdate(r.get("rally_date") or "", year)
        if not k or not start or not start.startswith(str(year)):
            continue
        e = slot(*k)
        e["date"], e["end"] = start, end
        place = _line(r.get("commint"), "장소")
        if place:
            e["place"] = place
        e["fee"] = _fee(r.get("options") or []) or e["fee"]
        e["divisions"] = _divisions(r.get("options") or []) or e["divisions"]
        if r.get("end_date"):
            e["deadline"] = r["end_date"][:10]
        e["regUrl"] = SOURCE["url"]
        if r.get("status") == "closed":
            e["closed"] = True
        if re.search(r"프로전", r.get("notification") or ""):
            e["major"] = True

    for v in viewers:  # 관람권: 날짜·장소 보조
        k = _kind(v.get("title"))
        start, end = parse_kdate(_line(v.get("commint"), "날짜") or "", year)
        if not k or not start or not start.startswith(str(year)):
            continue
        e = slot(*k)
        e["date"] = e["date"] or start
        e["place"] = e["place"] or _line(v.get("commint"), "장소")

    posts = _news_posts()
    log(f"  afex rally {len(rallies)} · 관람권 {len(viewers)} · 뉴스 {len(posts)}건")
    for name, start, end, place, pid in _from_posts(posts, year):
        k = _kind(name)
        if not k:
            continue
        e = slot(*k)
        if not e["date"]:
            e["date"], e["end"] = start, end
        e["place"] = e["place"] or place
        if e["url"] == SOURCE["url"]:
            e["url"] = NEWS
        if k[0] == "iron":
            e["host"] = "이승철 (AFEX 플랫폼 운영)"
            if not e["divisions"]:
                e["divisions"] = re.findall(r"(?m)^-\s*([^\n(]+)", posts[[p[0] for p in posts].index(pid)][3])[:12]

    if USE_SEASON_A and year == 2026:
        for key, start, end in SEASON_A:
            k = next(((kk, lb, mj) for kk, _, lb, mj in KINDS if kk == key), None)
            e = slot(*k)
            if not e["date"]:
                e["date"], e["end"] = start, end
                e["closed"] = True

    out = []
    for e in ev.values():
        if not e["date"]:
            continue
        e["city"] = _city(e["place"]) or ("부산" if "busan" in e["id"] else ("서울" if "seoul" in e["id"] else None))
        out.append(e)
    return sorted(out, key=lambda e: e["date"])
