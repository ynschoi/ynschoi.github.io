"""몬스터짐(World of Monsterzym) — https://event.monsterzym.com/

대회 목록은 메인 페이지 한 장에 서버 렌더링된 카드(.mz-card)로 나온다
(날짜 .mz-card-date-box, 구분 배지 .mz-card-badge, 대회명 .mz-card-title,
부제 .mz-card-subtitle, 설명 .mz-card-desc, 버튼 .mz-card-btn / .mz-card-link-btn).
시즌이 끝나면 카드가 내려가고 "2027년에 뵙겠습니다" 문구만 남는다.

주의: 이 사이트의 robots.txt는 'Disallow: /'(전체 크롤링 거부)이다.
그 설정이 유지되는 동안에는 아무 요청도 보내지 않고 빈 목록을 돌려준다.
"""
import re
import urllib.robotparser

from .common import UA, get, iso, log, parse_kdate, text, this_year

SOURCE = {"key": "monsterzym", "label": "몬스터짐 (World of Monsterzym)",
          "url": "https://event.monsterzym.com/"}

BASE = "https://event.monsterzym.com"
OVERSEAS = {"몽골": "MN", "울란바토르": "MN", "mongolia": "MN", "ulaanbaatar": "MN",
            "일본": "JP", "japan": "JP", "중국": "CN", "china": "CN", "태국": "TH", "thailand": "TH",
            "베트남": "VN", "vietnam": "VN", "필리핀": "PH", "philippines": "PH", "대만": "TW", "taiwan": "TW"}
DIV_WORDS = ["보디빌딩", "클래식 피지크", "클래식피지크", "맨즈 피지크", "맨즈피지크", "피지크", "비키니",
             "피규어", "웰니스", "우먼스 피지크", "피트니스", "스포츠모델", "bodybuilding",
             "classic physique", "men's physique", "bikini", "figure", "wellness", "women's physique"]


def _allowed():
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.parse(get(BASE + "/robots.txt").splitlines())
    except Exception as e:  # noqa: BLE001 — robots.txt를 못 읽으면 보수적으로 중단
        log(f"  [monsterzym] robots.txt 확인 실패({e}) — 수집 안 함")
        return False
    return rp.can_fetch(UA, BASE + "/")


def _cls(block, name):
    m = re.search(r'class="[^"]*\b%s\b[^"]*"[^>]*>(.*?)</(?:div|span|p|h\d|strong)>' % re.escape(name),
                  block, re.S)
    return text(m.group(1)) if m else ""


def _cards(page):
    starts = [m.start() for m in re.finditer(r'<div class="mz-card[\s"]', page)]
    for i, s in enumerate(starts):
        yield page[s:starts[i + 1] if i + 1 < len(starts) else s + 6000]


def _parse(block, year):
    title = _cls(block, "mz-card-title")
    if not title:
        return None
    sub = _cls(block, "mz-card-subtitle")
    badge = _cls(block, "mz-card-badge")
    desc = _cls(block, "mz-card-desc")
    when = _cls(block, "mz-card-date-box")
    date, end = parse_kdate(when, year)
    if not date:
        return None
    links = [(h if h.startswith("http") else BASE + h)
             for h in re.findall(r'class="mz-card-(?:link-)?btn[^"]*"[^>]*href="([^"#][^"]*)"', block)
             + re.findall(r'href="([^"#][^"]*)"[^>]*class="mz-card-(?:link-)?btn', block)]
    closed = "no-link" in block or "신청마감" in block
    name = f"{title} ({sub})" if sub else title
    blob = " ".join([title, sub, badge, desc]).lower()
    country = next((c for k, c in OVERSEAS.items() if k in blob), "KR")
    place = desc.split("\n")[0] if desc else None
    dl = re.search(r"(?:마감|deadline)[^\d]{0,10}([\d./\-년월일\s]+)", desc, re.I)
    fee = re.search(r"(?:참가비|등록비|fee)[^\d$₩]{0,10}([$₩]?[\d,]+\s*(?:원|USD|\$)?)", desc, re.I)
    divs = [d for d in DIV_WORDS if d.lower() in blob]
    is_pro = re.search(r"프로\s*쇼|pro\s*show|ifbb\s*pro", blob)
    is_q = re.search(r"퀄리파이어|qualifier", blob)
    return {
        "id": "monsterzym-" + re.sub(r"\W+", "_", f"{date}_{name}").strip("_").lower(),
        "src": "monsterzym", "fed": "몬스터짐", "name": name, "date": date, "end": end,
        "place": place, "city": None, "country": country,
        "fee": fee.group(1).strip() if fee else None,
        "deadline": parse_kdate(dl.group(1), year)[0] if dl else None,
        "divisions": divs or None,
        "qualification": "NPC 월드와이드 멤버십 가입 필수",
        "proCards": "IFBB 프로카드 수여" if is_q else None,
        "host": "몬스터짐", "url": SOURCE["url"],
        "regUrl": links[0] if links else None,
        "tier": "international" if country != "KR" or is_pro else "national",
        "major": bool(is_pro or is_q or re.search(r"챔피언|파이널|championship|final", blob)),
        "closed": closed,
    }


def crawl():
    if not _allowed():
        log("  [monsterzym] robots.txt가 크롤링을 금지(Disallow: /) — 수집 생략")
        return []
    page = get(SOURCE["url"])
    year = this_year()
    if "mz-card-title" not in page:
        log("  [monsterzym] 대회 카드 없음 (시즌 종료 안내만 게시됨)")
        return []
    out, seen = [], set()
    for b in _cards(page):
        ev = _parse(b, year)
        if ev and ev["date"] >= iso(year, 1, 1) and ev["id"] not in seen:
            seen.add(ev["id"])
            out.append(ev)
    log(f"  [monsterzym] {len(out)}건")
    return out
