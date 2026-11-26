"""머슬마니아 (MUSCLEMANIA)

1) 머슬마니아 코리아 — https://www.mmkorea.com/ (React SPA, 정적 프리렌더 텍스트 + JS 번들)
   홈 FAQ 텍스트에서 대회일·장소·접수기간을, JS 번들의 종목 안내(register/*.png 제목)에서
   종목을 읽는다. 참가비는 api.mmkorea.com(신청 API)에서만 내려와 읽지 않는다.
2) 세계 일정 — https://musclemania.com/musclemania-events-schedule/ 의 표들
   (섹션: PRO / USA & CANADA / INDIA / ASIA / CHINA / INTERNATIONAL)과
   표에서 링크한 'Show Info' 투어 페이지(장소·종목·참가비).
"""
import re

from .common import get, iso, log, text, this_year

MMK = "https://www.mmkorea.com/"
WORLD = "https://musclemania.com/musclemania-events-schedule/"
SOURCE = {"key": "musclemania", "label": "머슬마니아 (Musclemania)", "url": MMK}

MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"])}
COUNTRY = [  # (패턴, 국가코드) — 섹션 제목·쇼 이름·도시에서 찾는다
    (r"USA|CANADA|AMERICA|Los Angeles|Long Beach", "US"), (r"INDIA|Delhi|Hyderabad|Bangalore|Mumbai", "IN"),
    (r"CHINA|Yantai|Chengdu|Guangzhou|Xiamen", "CN"), (r"Philippines|Manila", "PH"),
    (r"Indonesia|Yogyakarta|Jakarta", "ID"), (r"Togo|Lom[eé]", "TG"), (r"Mexico", "MX"),
    (r"Korea|Seoul", "KR"), (r"Paris|France", "FR"), (r"United Kingdom|London|Britain", "GB"),
]


def _country(*ss):
    for s in ss:
        for pat, cc in COUNTRY:
            if re.search(pat, s or "", re.I):
                return cc
    return None


def _edate(s, year):
    """'November 20–21', 'December 20 – 21', 'December 5' → (start, end)"""
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2})(?:\s*[–\-]\s*(?:([A-Za-z]+)\s+)?(\d{1,2}))?", s or "")
    if not m or m.group(1).lower() not in MONTHS:
        return None, None
    mo = MONTHS[m.group(1).lower()]
    start = iso(year, mo, m.group(2))
    end = None
    if m.group(4):
        mo2 = MONTHS.get((m.group(3) or "").lower(), mo)
        end = iso(year + (1 if mo2 < mo else 0), mo2, m.group(4))
    return start, end


# ---------------------------------------------------------------- Korea
def _korea():
    try:
        home = get(MMK)
    except Exception as e:  # noqa: BLE001
        log(f"  ! mmkorea 실패: {e}")
        return []
    t = text(home)
    m = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*([^\n]*?)에서\s*개최", t)
    if not m:
        log("  - mmkorea 대회일 문구를 찾지 못함")
        return []
    start = iso(m.group(1), m.group(2), m.group(3))
    venue = m.group(4).strip()
    place, addr = venue, None
    pm = re.match(r"(.*?)\s*\((.*)\)\s*$", venue)
    if pm:
        place, addr = pm.group(1).strip(), pm.group(2).strip()
    city = None
    cm = re.match(r"\s*(서울|부산|대구|인천|광주|대전|울산|경기|제주)", addr or place)
    if cm:
        city = cm.group(1)
    deadline = None
    dm = re.search(r"참가\s*신청은\s*(\d{4})년\s*\d{1,2}월\s*\d{1,2}일부터\s*(\d{1,2})월\s*(\d{1,2})일까지", t)
    if dm:
        deadline = iso(dm.group(1), dm.group(2), dm.group(3))
    title = re.search(r"<title>([^<|]+)", home)
    name = text(title.group(1)).strip() if title else "머슬마니아 코리아"
    name = re.sub(r"^\s*20\d\d\s*", "", name)

    divisions = []
    js = re.search(r'src="(/assets/index-[^"]+\.js)"', home)
    if js:
        try:
            bundle = get(MMK.rstrip("/") + js.group(1))
            for d in re.findall(r'"register/[a-z_0-9]+\.png":\{title:`([^`\n]+)', bundle):
                d = re.sub(r"머슬마니아®\s*", "", d).strip()
                if d and d not in divisions:
                    divisions.append(d)
        except Exception as e:  # noqa: BLE001
            log(f"  ! mmkorea 번들 실패: {e}")
    if not divisions:
        lm = re.search(r"참가 가능한 종목은 무엇인가요\?\s*\n?\s*([^\n]+?)\s*종목에 참가", t)
        if lm:
            divisions = [x.strip() for x in lm.group(1).split(",") if x.strip()]
    return [{
        "id": f"musclemania-kr-{start[:4]}", "src": "musclemania", "fed": "MUSCLEMANIA",
        "name": name, "date": start, "end": None, "place": place, "city": city, "country": "KR",
        "fee": None, "deadline": deadline, "divisions": divisions,
        "host": "머슬마니아 코리아 (MMKorea)", "url": MMK, "regUrl": MMK + "apply/",
        "tier": "national", "major": True,
    }]


# ---------------------------------------------------------------- World
def _tour_info(url, show, cache):
    """투어 페이지에서 장소·종목·참가비. 실패하면 빈 dict. (페이지는 cache로 한 번만 받는다)"""
    if url not in cache:
        try:
            cache[url] = text(get(url))
        except Exception as e:  # noqa: BLE001
            log(f"  ! musclemania 투어 실패 {url}: {e}")
            cache[url] = ""
    t = cache[url]
    if not t:
        return {}
    info = {}
    # 여러 대회가 한 페이지에 있는 경우: 'NAME | December 12–13\n 장소…'
    blk = re.search(r"(?im)^\s*" + re.escape(show) + r"\s*[|I]\s*[A-Za-z]+\s+\d[^\n]*\n\s*([^\n]+)", t)
    loc = re.search(r"(?im)^\s*Location\s*\n\s*([^\n]+)", t)
    if blk:
        info["place"] = blk.group(1).strip()
    elif loc:
        info["place"] = loc.group(1).strip()
    dv = re.search(r"(?m)^\s*DIVISIONS\s*\n((?:[^\n]+\n){1,12}?)\s*(?:LOCATION|SCHEDULE|REGISTRATION)\b", t)
    if dv:
        info["divisions"] = [x.strip() for x in dv.group(1).split("\n") if x.strip()]
    fee = re.search(r"One Division\s*\n\s*Two Divisions\s*\n\s*Three Divisions\s*\n\s*([^\n$]*)\n\s*(\$\d+)\s*\n\s*(\$\d+)\s*\n\s*(\$\d+)", t)
    if fee:
        note = fee.group(1).strip()
        info["fee"] = f"1종목 {fee.group(2)} / 2종목 {fee.group(3)} / 3종목 {fee.group(4)}" + (f" ({note})" if note else "")
    head = re.search(r"(?m)^\s*([A-Z][a-z]+ \d{1,2}(?:\s*[–\-]\s*\d{1,2})?),\s*(\d{4})\s*$", t)
    if head:
        info["date"] = _edate(head.group(1), int(head.group(2)))
    return info


def _world():
    try:
        page = get(WORLD)
    except Exception as e:  # noqa: BLE001
        log(f"  ! musclemania 일정 실패: {e}")
        return []
    ym = re.search(r"(20\d\d)\s+EVENT SCHEDULE", page)
    year = int(ym.group(1)) if ym else this_year()
    rows = []  # (section, show, dates, city, link)
    pos = 0
    for tm in re.finditer(r"<table.*?</table>", page, re.S):
        heads = re.findall(r">\s*((?:20\d\d)\s+[^<]{2,40}SHOWS)\s*<", page[pos:tm.start()])
        section = text(heads[-1]) if heads else ""
        pos = tm.end()
        for tr in re.findall(r"<tr.*?</tr>", tm.group(0), re.S):
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)
            if len(cells) < 3:
                continue
            show, dates, city = (text(c) for c in cells[:3])
            if show.lower() == "show":
                continue
            link = re.search(r'href="([^"]+)"', cells[3]) if len(cells) > 3 else None
            rows.append((section, show, dates, city, link.group(1) if link else None))
    log(f"  musclemania 세계 일정 {len(rows)}행 ({year})")

    events, tours = {}, {}
    pro_rows = [r for r in rows if "PRO" in r[0].upper()]
    for section, show, dates, city, link in [r for r in rows if "PRO" not in r[0].upper()] + pro_rows:
        start, end = _edate(dates, year)
        if not start:
            continue
        is_pro = "PRO" in section.upper()
        same = next((e for e in events.values() if e["date"] == start and
                     (show.lower() in e["name"].lower() or e["name"].lower() in show.lower())), None)
        if is_pro and same:
            same["major"] = True
            continue
        country = _country(section if not re.search(r"ASIA|INTERNATIONAL|PRO", section, re.I) else "", show, city)
        if country == "KR":  # 한국 대회는 mmkorea에서
            continue
        key = re.sub(r"[^a-z0-9]+", "-", f"{show}-{start}".lower()).strip("-")
        info = _tour_info(link, show, tours) if link else {}
        d2 = info.get("date")
        if d2 and d2[0] and d2[0][:7] == start[:7]:  # 투어 페이지 날짜가 더 구체적이면 사용
            start, end = d2
        events[key] = {
            "id": f"musclemania-{key}", "src": "musclemania", "fed": "MUSCLEMANIA",
            "name": f"Musclemania {show.title() if show.isupper() else show}",
            "date": start, "end": end, "place": info.get("place"), "city": city or None,
            "country": country, "fee": info.get("fee"), "deadline": None,
            "divisions": info.get("divisions") or [], "host": "Musclemania / Fitness Universe",
            "url": link or WORLD, "regUrl": link, "tier": "international",
            "major": is_pro or bool(re.search(r"Pro|Universe|America|Nationals", show, re.I)),
        }
    return list(events.values())


def crawl():
    return sorted(_korea() + _world(), key=lambda e: e["date"])
