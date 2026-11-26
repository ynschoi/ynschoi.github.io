"""IFBB PRO KOREA / NPC Korea (ifbbprokorea.com) 대회 일정.

구조 (2026-11 확인, WordPress + Elementor):
  /schedule/ (전체 대회 일정) 에 모든 대회가 카드로 나열됨. 카드 = <h4> 대회명 + 아이콘 리스트
    e-far-calendar-alt 날짜 / e-far-clock 신청 마감 / e-fas-map-marker-alt 지역 /
    e-fas-map-pin 장소 / e-far-address-card 프로카드 / e-fas-trophy 종목 /
    e-fas-check-circle 참가 자격 + 버튼(상세 페이지 링크).
  카테고리 페이지(/schedule/open-regional/ 등)도 같은 카드 구조 — 전체 페이지에 없는 것만 보충.
  카드 컨테이너에 elementor-hidden-desktop/tablet/mobile 이 모두 붙으면 사이트에서 내린(종료) 대회.
  상세 페이지(/schedule/<slug>/): '📅 대회 날짜 / ⏱ 신청 마감 / 🏛 장소 / 📍 주소 / 참가비' 블록과
    Ninja Forms 참가 신청서(form.fields JSON) — 여기서 종목별 체급(class) 목록을 뽑는다.
  프로쇼 상세(/international/<slug>/): '🏆 Pro Division: ...' 줄.
카드에는 연도가 없어서, 페이지 본문의 'YYYY년 NPC' 등에서 시즌 연도를 추정한다.
"""
import json
import re
from collections import Counter
from datetime import datetime

import html as _html
import urllib.robotparser

from .common import KST, UA, get, iso, log, parse_kdate, text, this_year

SOURCE = {"key": "ifbbkorea", "label": "IFBB PRO KOREA (NPC 코리아)",
          "url": "https://ifbbprokorea.com/schedule/"}

BASE = "https://ifbbprokorea.com"
LIST_PAGES = ["/schedule/", "/schedule/open-regional/", "/schedule/natural-regional/",
              "/schedule/open-proqualifier/", "/schedule/natural-proqualifier/",
              "/schedule/ifbb-pro/"]
HOST = "IFBB PRO KOREA (AGP)"

ICON_FIELD = {
    "calendar-alt": "date", "calendar": "date", "clock": "deadline",
    "map-marker-alt": "city", "map-pin": "place", "address-card": "proCards",
    "trophy": "divisions", "check-circle": "qualification", "ticket-alt": "ticket",
}

EN2KO = {
    "fit model": "핏 모델", "bikini": "비키니", "wellness": "웰니스", "figure": "피겨",
    "men's physique": "멘즈 피지크", "mens physique": "멘즈 피지크",
    "classic physique": "클래식 피지크", "bodybuilding": "보디빌딩",
    "bodybuilding 212": "보디빌딩 212", "212 bodybuilding": "보디빌딩 212",
    "women's physique": "우먼즈 피지크", "womens physique": "우먼즈 피지크",
}

COUNTRY_HINT = [("필리핀", "PH"), ("philippines", "PH"), ("manila", "PH"), ("일본", "JP"),
                ("japan", "JP"), ("태국", "TH"), ("베트남", "VN"), ("중국", "CN"), ("대만", "TW")]


_ROBOTS = {}


def allowed(url):
    """robots.txt 확인 (호스트별 1회 로드). 읽기 실패 시 허용으로 간주."""
    host = re.match(r"https?://[^/]+", url).group(0)
    rp = _ROBOTS.get(host)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.parse(get(host + "/robots.txt", tries=1).splitlines())
        except Exception as e:  # noqa: BLE001
            log(f"  ! robots.txt 읽기 실패 {host}: {e} — 허용으로 간주")
            rp.parse([])
        _ROBOTS[host] = rp
    ok = rp.can_fetch(UA, url)
    if not ok:
        log(f"  - robots.txt 차단으로 건너뜀: {url}")
    return ok


def _lines(h):
    """줄 구조를 살린 텍스트 (태그 → 줄바꿈)."""
    h = re.sub(r"(?is)<(script|style|svg)[^>]*>.*?</\1>", " ", h)
    h = _html.unescape(re.sub(r"<[^>]+>", "\n", h))
    return "\n".join(x for x in (re.sub(r"\s+", " ", ln).strip() for ln in h.split("\n")) if x)


def _clean(s):
    return re.sub(r"\s+", " ", text(s)).strip()


def _season_year(htmls):
    """'2026년 NPC 오픈 리저널 참가 선수', '2026 NPC ...' 등에서 가장 많이 나온 연도."""
    c = Counter()
    for h in htmls:
        for y in re.findall(r"(20\d\d)\s*년?\s*NPC", h):
            c[int(y)] += 1
    return c.most_common(1)[0][0] if c else this_year()


def _date(s, year):
    s = re.sub(r"(\d{1,2})\s*[-~–]\s*(\d{1,2})\s*일", r"\1일~\2일", s or "")  # '9월 26-27일'
    return parse_kdate(s, year)


def _parse_cards(page_html):
    """카드 목록 → [{name, date_s, deadline_s, city, place, proCards, divisions, qualification,
    link, link_text, hidden}]"""
    out = []
    heads = list(re.finditer(r'<h4 class="elementor-heading-title[^"]*">(.*?)</h4>', page_html, re.S))
    for i, m in enumerate(heads):
        seg = page_html[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(page_html)]
        fields = {}
        for im in re.finditer(r'e-font-icon-svg e-fa[rsb]-([a-z-]+)".*?elementor-icon-list-text">(.*?)</span>',
                              seg, re.S):
            key = ICON_FIELD.get(im.group(1))
            if key and key not in fields:
                fields[key] = _clean(im.group(2))
        if "date" not in fields:
            continue
        links = re.findall(r'<a class="elementor-button[^"]*" href="([^"]+)"[^>]*>.*?elementor-button-text">(.*?)<',
                           seg, re.S)
        pre = page_html[:m.start()]
        k = pre.rfind("e-con-full")
        cont = pre[pre.rfind("<div", 0, k): pre.find(">", k)] if k >= 0 else ""
        hidden = all(f"elementor-hidden-{d}" in cont for d in ("desktop", "tablet", "mobile"))
        detail = next((u for u, _ in links if u.startswith(BASE) and
                       re.search(r"/(schedule|international|philippines)/[^/]+/?$", u)), None)
        out.append(dict(fields, name=re.sub(r"\s+", " ", _clean(m.group(1))), link=detail,
                        link_text=[_clean(t) for _, t in links], hidden=hidden))
    return out


def _form_fields(page_html):
    dec = json.JSONDecoder()
    fields = []
    for m in re.finditer(r"form\.fields\s*=\s*", page_html):
        try:
            f, _ = dec.raw_decode(page_html, m.end())
            fields += f
        except ValueError:
            pass
    return fields


def _short_class(c):
    c = re.sub(r"\s+", " ", c).strip()
    if re.search(r"\((?:[^)]*\d\s*(?:cm|kg))\)", c):
        return c
    return re.sub(r"\s*\(.*$", "", c).strip()


def _ko(div):
    d = div.replace("’", "'").strip()
    return EN2KO.get(d.lower(), d)


def _classes_from_form(page_html):
    """Ninja Forms 신청서 → (종목 목록, {종목: [체급...]}). 메인 '참가 종목 선택' + '[체급 선택] X' 만 사용."""
    divs, classes = [], {}
    for f in _form_fields(page_html):
        label = re.sub(r"<[^>]+>", "", str(f.get("label") or "")).strip()
        opts = [re.sub(r"<[^>]+>", "", str(o.get("label") or "")).strip() for o in f.get("options") or []]
        opts = [o for o in opts if o]
        if not opts:
            continue
        if label == "참가 종목 선택" and not divs:
            divs = [_ko(o) for o in opts]
        else:
            m = re.match(r"^\[체급 선택\]\s*(.+)$", label)
            if m:
                d = _ko(m.group(1))
                if d not in classes:
                    classes[d] = [_short_class(o) for o in opts]
    return divs, classes


def _detail(url, year):
    """상세 페이지 → dict(date, end, deadline, place, address, fee, divisions, classes, regUrl)"""
    if not allowed(url):
        return {}
    try:
        h = get(url)
    except Exception as e:  # noqa: BLE001
        log(f"  ! 상세 실패 {url}: {e}")
        return {}
    t = _lines(h)
    d = {}
    i = t.find("대회 날짜:")
    if i >= 0:
        j = t.find("대회 참가 절차", i)
        block = t[i: j if j > 0 else i + 1500]

        def line(key):
            m = re.search(key + r"[ \t]*:[ \t]*([^\n]+)", block)
            return m.group(1).strip() if m else None
        d["date"], d["end"] = _date(line("대회 날짜"), year)
        dl = line("신청 마감")
        if dl:
            d["deadline"] = _date(dl, year)[0]
        d["place"] = line("장소")
        addr = line("주소")
        d["address"] = addr if addr and "추후" not in addr else None
        fee = re.search(r"([^\n:]*참가비)[ \t]*:[ \t]*([^\n]+)", block)
        if fee:
            d["fee"] = fee.group(2).strip()
            add = re.search(r"무제한 종목 추가[ \t]*:[ \t]*([^\n(]+)", block)
            if add:
                d["fee"] += f" / 종목 추가 {add.group(1).strip()}"
    m = re.search(r"Pro Division\s*:\s*([^\n]+)", t)
    if m:
        d["divisions"] = [_ko(x) for x in re.split(r"\s*,\s*|\s+and\s+|\s*&\s*", m.group(1).strip()) if x]
    if not d.get("address"):
        m = re.search(r"Address\s*:\s*([^\n]+)", t)
        if m:
            d["address"] = m.group(1).strip()
    if "ifbbpromembership.com" in t:
        d["regUrl"] = "https://www.ifbbpromembership.com/"
    divs, classes = _classes_from_form(h)
    if divs or classes:
        d["formDivisions"] = divs
        d["regUrl"] = url  # 참가 신청서가 상세 페이지에 내장됨
    if classes:
        d["classes"] = classes
    return d


def _kind(name, link):
    n = name.replace(" ", "")
    slug = (link or "").rstrip("/").rsplit("/", 1)[-1]
    if "프로쇼" in n or "올스타" in n or "/international/" in (link or "") and "pq" not in slug:
        return "pro"
    if "퀄리파이어" in n or "아마추어올림피아" in n or "pq" in slug or slug == "aokorea":
        return "qualifier"
    if "내추럴리저널" in n or slug.startswith("natural-regional"):
        return "natural"
    if "리저널" in n:
        return "open"
    return "other"


def crawl():
    pages, cards = {}, []
    for p in LIST_PAGES:
        if not allowed(BASE + p):
            continue
        try:
            pages[p] = get(BASE + p)
        except Exception as e:  # noqa: BLE001
            log(f"  ! {p}: {e}")
    year = _season_year(pages.values())
    # 전체 일정 페이지 우선, 카테고리 페이지 카드는 (대회명, 날짜)가 같으면 병합만 한다.
    seen = {}
    for p, h in pages.items():
        for c in _parse_cards(h):
            for k in ("place", "city"):
                if c.get(k):
                    c[k] = re.sub(r"^(장소|지역)\s*:\s*", "", c[k])
            key = (re.sub(r"\s+|^NPC", "", c["name"]), _date(c["date"], year)[0])
            if key in seen:
                old = seen[key]
                for k, v in c.items():
                    if old.get(k) in (None, "", []) and v:
                        old[k] = v
                continue
            seen[key] = c
            cards.append(c)
    log(f"  ifbbkorea: 카드 {len(cards)}개 (시즌 {year})")

    today = datetime.now(KST).strftime("%Y-%m-%d")
    events, ids = [], Counter()
    for c in cards:
        date, end = _date(c["date"], year)
        if not date:
            continue
        det = _detail(c["link"], year) if c["link"] else {}
        kind = _kind(c["name"], c["link"])
        name = re.sub(r"^NPC\s+", "", c["name"]).strip()
        m = re.search(r"-pq-(\d+)/?$", c["link"] or "")
        if m and "#" not in name:  # 같은 이름의 회차 구분 (agp-natural-pq-1/-2)
            name += f" #{int(m.group(1))}"
        loc = " ".join(filter(None, [c.get("city"), c.get("place"), det.get("address")])).lower()
        country = next((cc for k, cc in COUNTRY_HINT if k in loc), "KR")
        divisions = det.get("divisions") or [x.strip() for x in re.split(r"\s*,\s*", c.get("divisions") or "")
                                             if x.strip()] or det.get("formDivisions")
        slug = (c["link"] or "").rstrip("/").rsplit("/", 1)[-1] or f"{date}-{name}"
        ids[slug] += 1
        eid = f"ifbbkorea-{slug}" + (f"-{ids[slug]}" if ids[slug] > 1 else "")
        qual = c.get("qualification")
        if qual:
            qual = re.sub(r"^참가 자격\s*:\s*", "", qual)
        pc = c.get("proCards")
        if pc:
            pc = re.sub(r"^프로 카드\s*:\s*", "", pc)
        ev = {
            "id": eid, "src": SOURCE["key"],
            "fed": {"pro": "IFBB PRO", "qualifier": "NPC"}.get(kind, "NPC"),
            "name": name,
            "date": date, "end": end or det.get("end"),
            "place": c.get("place") or det.get("place"),
            "city": c.get("city"),
            "address": det.get("address"),
            "country": country,
            "fee": det.get("fee"),
            "deadline": det.get("deadline") or (_date(c.get("deadline"), year)[0] if c.get("deadline") else None),
            "divisions": divisions or None,
            "divisionClasses": det.get("classes"),
            "qualification": qual,
            "proCards": pc,
            "host": HOST,
            "url": c["link"] or SOURCE["url"],
            "regUrl": det.get("regUrl"),
            "tier": "national" if country == "KR" else "international",
            "major": kind in ("pro", "qualifier"),
            "closed": bool(c["hidden"] or (end or date) < today),
        }
        if ev["deadline"] and ev["deadline"] > date:  # 연말 연도 넘김 보정
            ev["deadline"] = iso(int(ev["deadline"][:4]) - 1, ev["deadline"][5:7], ev["deadline"][8:])
        events.append({k: v for k, v in ev.items() if v is not None})
    events.sort(key=lambda e: (e["date"], e["name"]))
    return events
