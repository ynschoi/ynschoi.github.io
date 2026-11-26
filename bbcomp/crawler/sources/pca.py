"""PCA KOREA · NPCA (뉴빅터 포함) — 코치엔(coachn.co.kr)

PCA KOREA 공식 몰(www.pca-korea.com/mall)은 접수를 코치엔 앱으로 넘겨 대회 목록이 비어 있고,
코치엔 접수 목록은 '현재 회차'만, 상세는 마감 후 오류 페이지라서 출처 세 군데를 합친다.

  1) 접수 목록  /sub/competitions_list.php?sca=PCA접수|NPCA접수|NPCA뉴빅터접수
     → 현재 회차 대회명·날짜·참가비·마감여부. 상세가 열려 있으면 종목(select) 및 본문 텍스트의 장소/마감
  2) 매거진     /bbs/board.php?bo_table=magazine
     → 대회별 그랑프리 기사 첫 문장 "2026 년 11 월 1 일 김해 가야대학교에서 개최된 NPCA 부산 대회에서 ..."
        에서 날짜·장소·연맹·지역 (지난 대회 복원용)
  3) 순위표     /bbs/board.php?bo_table=ranking
     → "[NPCA 안산 순위]" 글의 종목 제목(18pt 굵은 글씨)으로 divisions 보충

ID는 연맹+날짜(+뉴빅터)로 만들어 출처가 바뀌어도 같은 대회는 같은 ID를 가진다 (crawl.py가 누적 보관).
"""
import html
import re
import urllib.parse
import urllib.robotparser
from datetime import date, datetime, timedelta

from .common import KST, get, iso, log, parse_kdate, text, this_year

COACHN = "https://coachn.co.kr"
SOURCE = {"key": "pca", "label": "PCA KOREA · NPCA (코치엔)", "url": f"{COACHN}/sub/competitions_list.php"}

CATS = {"PCA접수": "PCA", "NPCA접수": "NPCA", "NPCA뉴빅터접수": "NPCA"}
SKIP_WORDS = ("입장권", "사진", "영상", "메이크업", "헤어", "티켓")
MAX_MAG_PAGES = 30
CITY_EN = {
    "서울": "SEOUL", "부산": "BUSAN", "대구": "DAEGU", "인천": "INCHEON", "광주": "GWANGJU", "대전": "DAEJEON",
    "울산": "ULSAN", "세종": "SEJONG", "수원": "SUWON", "성남": "SEONGNAM", "고양": "GOYANG", "용인": "YONGIN",
    "부천": "BUCHEON", "안산": "ANSAN", "안양": "ANYANG", "시흥": "SIHEUNG", "화성": "HWASEONG", "김포": "GIMPO",
    "김해": "GIMHAE", "창원": "CHANGWON", "양산": "YANGSAN", "포항": "POHANG", "청주": "CHEONGJU",
    "천안": "CHEONAN", "제주": "JEJU", "전북": "JEONBUK", "전남": "JEONNAM", "경남": "GYEONGNAM",
    "경북": "GYEONGBUK", "강원": "GANGWON", "원주": "WONJU", "춘천": "CHUNCHEON", "순천": "SUNCHEON",
    "여수": "YEOSU", "평택": "PYEONGTAEK", "파주": "PAJU", "안성": "ANSEONG", "양평": "YANGPYEONG",
    "충청": "CHUNGCHEONG", "의정부": "UIJEONGBU", "남양주": "NAMYANGJU", "강남": "GANGNAM", "강북": "GANGBUK",
}
SPECIAL = {"슈퍼시리즈": "SUPER SERIES", "아시아챔피언쉽": "ASIAN CHAMPIONSHIP LEAGUE",
           "아시아챔피언십": "ASIAN CHAMPIONSHIP LEAGUE", "아시안챔피언쉽": "ASIAN CHAMPIONSHIP LEAGUE"}
EN_CITY = {v: k for k, v in CITY_EN.items()}


# ---------------------------------------------------------------- robots.txt
_robots = {}


def allowed(url):
    """robots.txt 확인 (urllib.robotparser + '*' 와일드카드 Disallow 보완). 못 읽으면 허용."""
    p = urllib.parse.urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp, wild = urllib.robotparser.RobotFileParser(), []
        try:
            body = get(base + "/robots.txt", tries=1)
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


def fetch(url, params=None):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    return get(url) if allowed(url) else None


# ---------------------------------------------------------------- helpers
def nospace(s):
    return re.sub(r"\s+", "", s or "")


def is_nv(s):
    return bool(re.search(r"뉴빅터|NEW\s*VICTOR", s or "", re.I))


def event_name(region, nv=False):
    """'부산' → 'BUSAN POINT LEAGUE', '슈퍼 시리즈' → 'SUPER SERIES', 그 외는 원문 유지."""
    r = nospace(region)
    if nv:
        return "NEW VICTOR SERIES" + (f" IN {CITY_EN[r]}" if r in CITY_EN else "")
    if r in SPECIAL:
        return SPECIAL[r]
    if r in CITY_EN:
        return f"{CITY_EN[r]} POINT LEAGUE"
    return (region or "").strip()


def region_key(name):
    """이름/지역 → 비교용 키 ('SEOUL POINT LEAGUE'·'서울' → '서울')."""
    n = nospace(name).upper()
    m = re.match(r"([A-Z]+)POINTLEAGUE", n)
    if m and m.group(1) in EN_CITY:
        return EN_CITY[m.group(1)]
    for k, v in SPECIAL.items():
        if nospace(v).upper() == n:
            return "슈퍼시리즈" if "SUPER" in v else "아시아챔피언쉽"
    n = nospace(name)
    if n in ("아시아챔피언십", "아시안챔피언쉽"):
        return "아시아챔피언쉽"
    return n


def make_event(fed, d, nv=False, **kw):
    ev = {"id": f"pca-{fed.lower()}-{d}" + ("-nv" if nv else ""), "fed": fed, "date": d, "end": None,
          "country": "KR", "tier": "national", "host": "PCA KOREA",
          "regUrl": f"{COACHN}/sub/competitions_list.php?sca="
                    + urllib.parse.quote("NPCA뉴빅터접수" if nv else f"{fed}접수")}
    ev.update(kw)
    ev["major"] = bool(re.search(r"SUPER SERIES|CHAMPIONSHIP|FINAL|챔피언|파이널", ev.get("name") or "", re.I))
    return ev


def clean_division(s):
    s = re.sub(r"\s+", " ", html.unescape(s or "")).strip(" :·-")
    return s


# ---------------------------------------------------------------- 1) 코치엔 접수 목록 + 상세
def parse_detail(body):
    """상세 페이지 → (divisions, place, deadline). 마감 후 오류 페이지면 None."""
    if "alertPopUP(\"" in body and "option_container" not in body and "market_txt" not in body:
        return None
    divs = []
    for opt in re.findall(r'<select[^>]*class_select[^>]*>(.*?)</select>', body, re.S)[:1]:
        for v, label in re.findall(r'<option value="([^"]*)"[^>]*>(.*?)</option>', opt, re.S):
            label = clean_division(text(label))
            if v and label and label not in divs:
                divs.append(label)
    m = re.search(r'<div class="market_txt">(.*?)</div>\s*<div>', body, re.S)
    t = text(m.group(1)) if m else ""
    place = deadline = None
    mp = re.search(r"(?:장\s*소|대회\s*장소|장소)\s*[:：]\s*([^\n]+)", t)
    if mp:
        place = mp.group(1).strip()[:80]
    md = re.search(r"(?:접수\s*마감|마감\s*일?|신청\s*마감)[^\n0-9]{0,10}([^\n]+)", t)
    if md:
        deadline = parse_kdate(md.group(1))[0]
    return divs, place, deadline


def crawl_coachn():
    year_now = this_year()
    out = []
    for sca, fed in CATS.items():
        list_url = f"{COACHN}/sub/competitions_list.php?sca={urllib.parse.quote(sca)}"
        body = fetch(list_url)
        if body is None:
            continue
        for box in re.findall(r'<div class="box">(.*?)</div><!-- \.box end -->', body, re.S):
            m_id = re.search(r"competitions_info\.php\?id=(\d+)", box)
            m_t = re.search(r'<p style="margin-bottom: 5px;">(.*?)</p>', box, re.S)
            if not (m_id and m_t):
                continue
            title = text(m_t.group(1))
            if any(w in title for w in SKIP_WORDS):
                continue
            m_y = re.search(r"(20\d\d)", title)
            start, end = parse_kdate(title, int(m_y.group(1)) if m_y else year_now)
            if not start:
                log(f"  - 날짜 없음, 건너뜀: {title}")
                continue
            m_fee = re.search(r"<strong>([\d,]+)원</strong>", box)
            status = text(re.search(r"마감일시 카운트다운 -->(.*?)<!-- 가격", box, re.S).group(1)) \
                if "마감일시 카운트다운" in box else ""
            name = re.sub(r"\s*\(\s*\d{1,2}\s*월[^)]*\)\s*", " ", title)
            name = re.sub(r"^\s*20\d\d\s*", "", name).strip()
            name = re.sub(r"^N?PCA\s+", "", name).strip()
            nv = sca == "NPCA뉴빅터접수" or is_nv(title)
            detail_url = f"{COACHN}/sub/competitions_info.php?id={m_id.group(1)}"
            divs = place = deadline = None
            dbody = fetch(detail_url)
            got = parse_detail(dbody) if dbody else None
            if got:
                divs, place, deadline = got
            ev = make_event(fed, start, nv, name=name, end=end, fee=f"{m_fee.group(1)}원" if m_fee else None,
                            place=place, deadline=deadline, divisions=divs or None,
                            url=detail_url if got else list_url, regUrl=list_url,
                            status=status or None, closed=("마감" in status) or None)
            out.append(ev)
        log(f"  coachn {sca}: 누적 {len(out)}건")
    return out


# ---------------------------------------------------------------- 2) 매거진 (지난 대회)
MAG_RE = re.compile(
    r"(20\d\d)\s*년?\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*(?:[,~\-]\s*(\d{1,2})\s*일\s*)?,?\s*"
    r"(.{2,40}?)\s*에서\s*(?:개최된|열린|진행된)\s*((?:N?PCA\s*/?\s*,?\s*)+)(.+?)\s*(?:피트니스\s*)?대회")


def parse_mag_sentence(t):
    m = MAG_RE.search(t)
    if not m:
        return None
    y, mo, d1, d2, place, feds, region = m.groups()
    feds = re.findall(r"N?PCA", feds)
    region = re.sub(r"\s*(피트니스|대회)$", "", region.strip())
    res = []
    for i, fed in enumerate(feds):
        day = d2 if (i > 0 and d2) else d1
        res.append((fed, iso(y, mo, day), place.strip(), region))
    return res


def crawl_magazine(min_year):
    base = f"{COACHN}/bbs/board.php?bo_table=magazine"
    posts, seen = [], set()
    for page in range(1, MAX_MAG_PAGES + 1):
        body = fetch(base, {"page": page})
        if body is None:
            break
        new = 0
        for wid, inner in re.findall(r'href="[^"]*bo_table=magazine&(?:amp;)?wr_id=(\d+)[^"]*"[^>]*>(.*?)</a>', body, re.S):
            t = text(inner)
            if not t or wid in seen:
                continue
            seen.add(wid)
            new += 1
            posts.append((int(wid), t))
        if not new:
            break
        # 목록 마지막 글에 연도가 이전 해로 보이면 중단 ('2025 ...' 제목)
        if any(re.match(r"\s*(20\d\d)\b", t) and int(re.match(r"\s*(20\d\d)", t).group(1)) < min_year
               for _, t in posts[-new:]):
            break
    # 연속된 같은 [태그] 글을 한 묶음으로 → 묶음당 날짜 문장이 나올 때까지 최대 3개 열람
    clusters, last = [], None
    for wid, t in sorted(posts, reverse=True):
        m = re.match(r"\s*\[([^\]]+)\]", t)
        if not m:
            last = None
            continue
        raw = re.sub(r"\s*프로전\s*$", "", m.group(1).strip())
        tag = nospace(raw)
        if tag != last:
            mt = re.match(r"((?:N?PCA\s*[,/]?\s*)+)(.+)$", raw)
            clusters.append((mt.group(2).strip() if mt else None, []))
            last = tag
        clusters[-1][1].append(wid)
    found = {}
    for tag_region, wids in clusters:
        for wid in wids[:3]:
            body = fetch(f"{base}&wr_id={wid}")
            if body is None:
                break
            m = re.search(r'id="bo_v_con">(.*?)</div>', body, re.S)
            res = parse_mag_sentence(text(m.group(1)) if m else "")
            if res:
                for fed, d, place, region in res:
                    # 기사 본문의 지역명이 틀린 경우가 있어(예: [PCA 수원] 글에 'PCA 천안') 제목 태그 우선
                    region = tag_region or region
                    if int(d[:4]) >= min_year:
                        found.setdefault((fed, d, region_key(region)), (place, region, f"{base}&wr_id={wid}"))
                break
    log(f"  coachn 매거진: 글 {len(posts)}개, 묶음 {len(clusters)}개 → 대회 {len(found)}건")
    return found


# ---------------------------------------------------------------- 3) 순위표 (종목)
def ranking_list():
    base = f"{COACHN}/bbs/board.php?bo_table=ranking"
    out, seen = [], set()
    today = datetime.now(KST).date()
    for page in range(1, 20):
        body = fetch(base, {"page": page})
        if body is None:
            break
        new = 0
        for li in re.findall(r"<li[^>]*>(.*?)</li>", body, re.S):
            m = re.search(r"bo_table=ranking&(?:amp;)?wr_id=(\d+)", li)
            if not m or m.group(1) in seen:
                continue
            t = text(li)
            mt = re.search(r"\[\s*(N?PCA)\s+(.+?)\s*순위\s*\]", t)
            if not mt:
                continue
            seen.add(m.group(1))
            new += 1
            md = re.search(r"(?:(\d{2})-)?(\d{2})-(\d{2})\s+[\d,]+\s*회", t)
            if md:
                y = 2000 + int(md.group(1)) if md.group(1) else today.year
                posted = date(y, int(md.group(2)), int(md.group(3)))
                if posted > today:
                    posted = date(y - 1, posted.month, posted.day)
            else:
                posted = today  # 오늘 쓴 글은 시각(HH:MM)만 표시
            out.append({"wid": m.group(1), "fed": mt.group(1), "region": mt.group(2), "posted": posted})
        if not new:
            break
    return out


def ranking_divisions(wid):
    body = fetch(f"{COACHN}/bbs/board.php?bo_table=ranking&wr_id={wid}")
    if not body:
        return []
    m = re.search(r'id="bo_v_con">(.*?)</div>', body, re.S)
    divs = []
    for h in re.findall(r"font-size:\s*18pt[^>]*>\s*<b>(.*?)</b>", m.group(1) if m else "", re.S):
        h = clean_division(text(h))
        if h and h not in divs:
            divs.append(h)
    return divs


# ---------------------------------------------------------------- crawl
def crawl():
    year = this_year()
    events = {}

    def key(e):
        return (e["fed"], e["date"], region_key(e.get("name")))

    for e in crawl_coachn():
        if int(e["date"][:4]) >= year:
            events[key(e)] = e

    mag = crawl_magazine(year)
    # 기사 날짜 오기 보정: PCA(토)·NPCA(일) 주말 개최인데 PCA 기사가 같은 지역 NPCA와 같은 일요일로 적힌 경우 → 토요일
    for (fed, d, rk) in list(mag):
        if fed == "PCA" and date.fromisoformat(d).weekday() == 6 and ("NPCA", d, rk) in mag:
            sat = (date.fromisoformat(d) - timedelta(days=1)).isoformat()
            log(f"  - PCA {rk} {d}(일) → {sat}(토)로 보정 (NPCA와 같은 날로 적힘)")
            mag[("PCA", sat, rk)] = mag.pop((fed, d, rk))
    for (fed, d, rk), (place, region, url) in mag.items():
        nv = is_nv(region)
        e = make_event(fed, d, nv, name=event_name(region, nv), place=place, url=url, closed=True)
        k = key(e)
        if k in events:
            events[k]["place"] = events[k].get("place") or place
            continue
        events[k] = e

    # 순위표 → 같은 연맹·지역의, 글 작성일 이전 가장 최근 대회에 종목 보충
    today = datetime.now(KST).date().isoformat()
    by_region = {}
    for e in events.values():
        if e["date"] <= today:
            by_region.setdefault((e["fed"], region_key(e["name"])), []).append(e)
    used = set()
    for r in ranking_list():
        cands = [e for e in by_region.get((r["fed"], region_key(r["region"])), [])
                 if e["date"] <= r["posted"].isoformat()
                 and e["date"] >= (r["posted"] - timedelta(days=150)).isoformat() and e["id"] not in used]
        if not cands:
            continue
        e = max(cands, key=lambda x: x["date"])
        used.add(e["id"])
        if not e.get("divisions"):
            divs = ranking_divisions(r["wid"])
            if divs:
                e["divisions"] = divs
                e["resultUrl"] = f"{COACHN}/bbs/board.php?bo_table=ranking&wr_id={r['wid']}"

    out = sorted(events.values(), key=lambda e: (e["date"], e["fed"]))
    log(f"  pca: {len(out)}건 (종목 {sum(1 for e in out if e.get('divisions'))}, "
        f"장소 {sum(1 for e in out if e.get('place'))})")
    return out
