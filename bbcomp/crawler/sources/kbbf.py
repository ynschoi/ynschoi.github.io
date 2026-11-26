"""대한보디빌딩협회 (KBBF) — https://bodybuilding.or.kr

  /contest_kr   국내대회 (Mr.&Ms. Korea, 전국체전, 생활체육대축전, YMCA 등)
  /contest_city 시·도대회 (시도 선발전, 시장배·도지사배 등)
게시판이 연도 카테고리(2026, 2025 …)로 나뉘어 있다. 글 본문에 '대회일시/일자, 대회장소/장소, 주최, 접수 마감일'이 텍스트로 있다.
robots.txt: '/?mode*'만 금지.

※ 이 사이트는 일부 클라우드 IP에서 '접근 제한'을 띄운다. GitHub Actions에서는 정상 응답한다.
  이 환경에서 403이면 그냥 실패로 두고(우회하지 않음) 이전 데이터를 유지한다.
"""
import html
import re

from .common import get, log, parse_kdate, text, this_year

BASE = "https://bodybuilding.or.kr"
SOURCE = {"key": "kbbf", "label": "대한보디빌딩협회 (국내·시도대회)", "url": f"{BASE}/contest_kr"}
UA = {"User-Agent": "Mozilla/5.0 (compatible; bbcomp-schedule-bot/1.0; weekly personal schedule page)"}
BOARDS = [("contest_kr", "national"), ("contest_city", "regional")]
LABELS = ["대회명", "대회일시", "일 자", "일자", "대회장소", "장 소", "장소", "주최 및 주관", "주 최", "주최", "주 관", "주관",
          "후 원", "후원", "협 찬", "협찬", "접수 마감일", "접수마감일", "참가비", "신청하기"]
MAX_PAGES = 6


def _year_categories(page):
    """'2026' → category id."""
    out = {}
    for cid, label in re.findall(r"_category_([A-Za-z0-9]+)\"[^>]*>(20\d\d)</li>", page):
        out[label] = cid
    return out


def _fields(detail):
    m = re.search(r'class="[^"]*fr-view[^"]*"[^>]*>(.*?)(?:댓글을 불러오는 중|class="postmeta)', detail, re.S)
    body = text(m.group(1)) if m else text(detail)
    body = re.sub(r"\s+", " ", body)
    pat = "|".join(re.escape(l) for l in sorted(LABELS, key=len, reverse=True))
    parts = re.split(rf"\s*({pat})\s*[:：]?\s*", body)
    f = {}
    for i in range(1, len(parts) - 1, 2):
        k = re.sub(r"\s+", "", parts[i])
        v = parts[i + 1].strip()
        if v and k not in f:
            f[k] = v[:200]
    return f, body


def crawl():
    events, seen = [], set()
    years = {str(this_year()), str(this_year() + 1)}
    for board, tier in BOARDS:
        first = get(f"{BASE}/{board}", headers=UA)
        cats = _year_categories(first)
        for y in sorted(years & set(cats)):
            for page in range(1, MAX_PAGES + 1):
                lst = get(f"{BASE}/{board}/", {"category": cats[y], "page": page}, headers=UA)
                items = re.findall(r'href="(/' + board + r'/\?[^"]*bmode=view&(?:amp;)?idx=(\d+)[^"]*)"[^>]*>\s*<span>\s*(.*?)\s*</span>',
                                   lst, re.S)
                new = [(html.unescape(u), idx, text(t)) for u, idx, t in items if idx not in seen]
                if not new:
                    break
                for url, idx, title in new:
                    seen.add(idx)
                    try:
                        d = get(BASE + url, headers=UA)
                    except Exception as e:  # noqa: BLE001
                        log(f"  ! kbbf {idx}: {e}")
                        continue
                    f, body = _fields(d)
                    when = f.get("대회일시") or f.get("일자") or ""
                    start, end = parse_kdate(when, int(y))
                    if not start:
                        start, end = parse_kdate(body, int(y))
                    if not start:
                        log(f"  - kbbf 날짜 없음: {title}")
                        continue
                    dl = f.get("접수마감일")
                    deadline = parse_kdate(dl, int(y))[0] if dl else None
                    host = f.get("주최및주관") or f.get("주최")
                    name = re.sub(r"\s*\((?:참가신청 연장|접수 연장)[^)]*\)\s*", " ", f.get("대회명") or title).strip()
                    events.append({
                        "id": f"kbbf-{idx}", "fed": "KBBF", "name": name,
                        "date": start, "end": end,
                        "place": (f.get("대회장소") or f.get("장소") or "").split(" 주")[0].strip() or None,
                        "deadline": deadline, "host": host, "url": BASE + url.split("&t=board")[0] + "&t=board",
                        "regUrl": BASE + url, "tier": tier, "country": "KR",
                        "major": tier == "national" and bool(re.search(r"Korea|코리아|전국체육대회|국가대표", name, re.I)),
                    })
                log(f"  kbbf {board} {y} p{page}: {len(new)}건")
    return events
