"""NABBA KOREA — https://nabba.kr/board/com_schedule.html

일정 페이지의 카드(.nabba-event-card*)에 대회명·날짜·장소, 신청 버튼에 접수기간(data-end-date)이 있다.
버튼 링크(쇼핑몰 카테고리 product/list.html?cate_no=N, 또는 board/XX.html 안내 페이지)의 상품명
'2026 GP BODYBUILDING' 등에서 종목을, 첫 종목 상품 페이지 JSON-LD의 옵션 가격에서 참가비를 뽑는다.
버튼 링크는 nabba1950.cafe24.com(같은 쇼핑몰의 원 도메인)으로 걸려 있어 nabba.kr로 바꿔 요청한다.
robots.txt 금지 경로(/api/, /order/ 등)는 쓰지 않으며 요청 전에 확인한다.
브라우저 UA는 cafe24 봇 챌린지로 리다이렉트되므로 크롤러 UA(HEADERS)를 밝혀 요청한다.
"""
import html
import re
import urllib.parse
import urllib.robotparser

from .common import get, log, parse_kdate, text, this_year

BASE = "https://nabba.kr"
SOURCE = {"key": "nabba", "label": "NABBA KOREA", "url": f"{BASE}/board/com_schedule.html"}

NOT_DIVISION = re.compile(r"photo|video|care|tan\b|hair|makeup|추가|영상|사진|서비스|쉐이크|패치|\+", re.I)
# 브라우저 UA로 요청하면 cafe24 봇 챌린지(JS) 페이지로 302 된다 → 크롤러임을 밝히는 UA 사용
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bbcomp-schedule-bot/1.0)"}
MAJOR = re.compile(r"CHAMPIONSHIP|GRAND\s*PRIX|PRO\s*SHOW|FINAL|챔피언|그랑프리|파이널", re.I)

# ---------------------------------------------------------------- robots.txt
_robots = {}


def allowed(url):
    """robots.txt 확인 (urllib.robotparser + '*' 와일드카드 Disallow 보완). 못 읽으면 허용."""
    p = urllib.parse.urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp, wild = urllib.robotparser.RobotFileParser(), []
        try:
            body = get(base + "/robots.txt", headers=HEADERS, tries=1)
            lines = body.splitlines()
            if "<html" in body[:500].lower():
                lines = []
        except Exception:  # noqa: BLE001  (404 등 → 규칙 없음)
            lines = []
        rp.parse(lines)
        star = False
        for ln in lines:
            k, _, v = ln.partition(":")
            k, v = k.strip().lower(), v.split("#")[0].strip()
            if k == "user-agent":
                star = v == "*"
            elif k == "disallow" and star and "*" in v:
                wild.append(re.compile(re.escape(v).replace(r"\*", ".*").replace(r"\$", "$")))
        _robots[base] = (rp, wild)
    rp, wild = _robots[base]
    path = p.path + ("?" + p.query if p.query else "")
    ok = rp.can_fetch("*", url) and not any(w.match(path) for w in wild)
    if not ok:
        log(f"  - robots.txt 금지, 건너뜀: {url}")
    return ok


def fetch(url):
    if not allowed(url):
        return None
    try:
        return get(url, headers=HEADERS)
    except Exception as e:  # noqa: BLE001
        log(f"  ! {url}: {e}")
        return None


def local(url):
    """nabba1950.cafe24.com 링크 → nabba.kr 같은 경로."""
    p = urllib.parse.urlsplit(urllib.parse.urljoin(BASE + "/", html.unescape(url or "")))
    if p.netloc.endswith("cafe24.com") or p.netloc.endswith("nabba.kr"):
        return urllib.parse.urlunsplit(("https", "nabba.kr", p.path, p.query, ""))
    return None


# ---------------------------------------------------------------- 상세(종목·참가비)
def category_products(url):
    """카테고리 목록 → (카테고리 라벨, [(상품명, 상품 URL)])."""
    body = fetch(url)
    if not body:
        return None, []
    loc = re.search(r"현재 위치(.*?)</div>", body, re.S)
    label = text(loc.group(1)).split()[-1] if loc and text(loc.group(1)) else None
    items = []
    for href, name in re.findall(
            r'<div class="name"><a href="(/product/[^"]+)"[^>]*>.*?font-weight:bold;">([^<]+)</span></a>', body, re.S):
        items.append((html.unescape(name).strip(), BASE + href))
    return label, items


def detail(link):
    """신청 링크 → (divisions, fee, url). board/XX.html 이면 그 안의 카테고리 링크를 따라간다."""
    url = local(link)
    if not url:
        return [], None, None
    cats = [url]
    if "/board/" in url:
        body = fetch(url) or ""
        cats = [local(h) for h in re.findall(r'href="([^"]*product/list\.html\?cate_no=\d+)"', body)]
        cats = [c for c in dict.fromkeys(cats) if c]
    divs, first = [], None
    for c in cats:
        label, items = category_products(c)
        for name, purl in items:
            m = re.match(r"\s*20\d\d\s+([A-Z0-9]+)\s+(.+)$", name)
            if not m or NOT_DIVISION.search(name):
                continue
            # 다른 대회 상품이 섞여 있는 카테고리 대비: 카테고리 라벨(GP, AOC 등)과 약어가 같은 것만
            if label and re.fullmatch(r"[A-Z0-9]+", label) and m.group(1) != label:
                continue
            d = m.group(2).strip()
            if d not in divs:
                divs.append(d)
                first = first or purl
    fee = None
    if first:
        body = fetch(first) or ""
        prices = sorted({int(p) for p in re.findall(r'"price"\s*:\s*"?(\d+)', body) if int(p) > 0})
        if prices:
            fee = f"{prices[0]:,}원" if len(prices) == 1 else f"{prices[0]:,}~{prices[-1]:,}원"
    return divs, fee, url


# ---------------------------------------------------------------- crawl
def crawl():
    body = get(SOURCE["url"], headers=HEADERS) if allowed(SOURCE["url"]) else ""
    year = this_year()
    out = []
    for card in re.split(r'<div class="nabba-event-card2?">', body)[1:]:
        m_t = re.search(r'<h3 class="event-title">(.*?)</h3>', card, re.S)
        m_d = re.search(r'<p class="event-date">(.*?)</p>', card, re.S)
        if not (m_t and m_d):
            continue
        title = text(m_t.group(1))
        start, end = parse_kdate(text(m_d.group(1)))
        if not start or int(start[:4]) < year:
            continue
        m_p = re.search(r'<p class="event-place">(.*?)</p>', card, re.S)
        place = re.sub(r"^\s*장소\s*:\s*", "", text(m_p.group(1))) if m_p else None
        m_a = re.search(r'<a href="([^"]*)"[^>]*class="event-link"([^>]*)>', card, re.S)
        link = m_a.group(1) if m_a else None
        attrs = m_a.group(2) if m_a else ""
        m_end = re.search(r'data-end-date="(\d{4}-\d\d-\d\d)', attrs)
        m_open = re.search(r'data-open-date="(\d{4}-\d\d-\d\d)', attrs)
        divs, fee, url = detail(link) if link else ([], None, None)
        name = re.sub(r"^\s*(20\d\d\s+)?(NABBA\s+)?", "", title).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        out.append({
            "id": f"nabba-{start[:4]}-{slug}", "fed": "NABBA", "name": name,
            "date": start, "end": end, "place": place or None, "country": "KR",
            "fee": fee, "deadline": m_end.group(1) if m_end else None,
            "regOpen": m_open.group(1) if m_open else None,
            "divisions": divs or None, "host": "NABBA KOREA",
            "url": SOURCE["url"], "regUrl": url,
            "tier": "international" if re.search(r"ASIA|WORLD|INTERNATIONAL|PRO", name, re.I) else "national",
            "major": bool(MAJOR.search(name)),
        })
    log(f"  nabba: {len(out)}건 (종목 {sum(1 for e in out if e.get('divisions'))})")
    return out
