"""해외 IFBB Pro League / NPC Worldwide 대회 일정.

출처 조사 결과 (2026-11):
  * www.ifbbpro.com — 모든 페이지(/schedule/, /wp-json/…)가 봇 검증 대기 페이지
    ('One moment, please...' + JS reload)를 반환해 표준 라이브러리 요청으로는 내용을 받을 수 없다.
    robots.txt 상 Crawl-Delay 10. 아래 _ifbbpro_shows()는 tribe REST/iCal 을 한 번씩 시도하고
    검증 페이지면 로그만 남기고 건너뛴다 (우회하지 않음).
  * npcnewsonline.com — 'Contest Schedule' 캘린더(Stachethemes Event Calendar)의 공개 REST
    /wp-json/stec/v2/get/calendars/<id>/events/<YYYY-MM-DD>/<YYYY-MM-DD> 가 JSON 을 준다.
    카테고리: 'NPC Worldwide'(해외 아마추어), 'National Physique Committee'(미국 NPC),
    'Canadian Physique Alliance', 'Natural' + 종목 카테고리(Bikini, Men's Physique, ...).
    IFBB 프로쇼는 이 캘린더에 없다.
기본은 NPC Worldwide 만 수집(fed='NPC WW'). INCLUDE_NPC_USA=True 면 미국 NPC 대회도 포함(fed='NPC').
한국 대회(country='KR')도 그대로 두고 표시만 한다 — 중복 제거는 상위에서.
"""
import html
import json
import re
import urllib.robotparser
from datetime import datetime

from .common import KST, UA, get, log, this_year

SOURCE = {"key": "ifbbpro_world", "label": "IFBB Pro League / NPC Worldwide (해외)",
          "url": "https://npcnewsonline.com/schedule/"}

NPCNEWS = "https://npcnewsonline.com"
STEC_CAL_DEFAULT = 686587  # 'Contest Schedule'
IFBBPRO = "https://www.ifbbpro.com"
IFBBPRO_DELAY = 10  # robots.txt Crawl-Delay
INCLUDE_NPC_USA = False

NON_DIVISION_CATS = {"NPC Worldwide", "National Physique Committee", "Canadian Physique Alliance",
                     "Natural"}

COUNTRY_ISO = {
    "south korea": "KR", "korea": "KR", "korea, republic of": "KR", "republic of korea": "KR", "japan": "JP", "china": "CN",
    "taiwan": "TW", "hong kong": "HK", "philippines": "PH", "thailand": "TH", "vietnam": "VN",
    "malaysia": "MY", "singapore": "SG", "indonesia": "ID", "india": "IN", "kazakhstan": "KZ",
    "australia": "AU", "new zealand": "NZ", "usa": "US", "united states": "US", "canada": "CA",
    "mexico": "MX", "brazil": "BR", "argentina": "AR", "chile": "CL", "colombia": "CO", "peru": "PE",
    "paraguay": "PY", "uruguay": "UY", "bolivia": "BO", "panama": "PA", "costa rica": "CR",
    "guatemala": "GT", "el salvador": "SV", "dominican republic": "DO", "bahamas": "BS",
    "trinidad and tobago": "TT", "uk": "GB", "united kingdom": "GB", "england": "GB", "ireland": "IE",
    "spain": "ES", "portugal": "PT", "france": "FR", "germany": "DE", "italy": "IT",
    "netherlands": "NL", "belgium": "BE", "luxembourg": "LU", "switzerland": "CH", "austria": "AT",
    "poland": "PL", "czech republic": "CZ", "slovakia": "SK", "hungary": "HU", "romania": "RO",
    "bulgaria": "BG", "serbia": "RS", "ukraine": "UA", "russia": "RU", "estonia": "EE",
    "latvia": "LV", "lithuania": "LT", "sweden": "SE", "norway": "NO", "denmark": "DK",
    "finland": "FI", "israel": "IL", "south africa": "ZA", "angola": "AO", "mozambique": "MZ",
    "uae": "AE", "united arab emirates": "AE", "saudi arabia": "SA", "turkey": "TR", "greece": "GR",
}

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


def _crawl_delay(url, default):
    rp = _ROBOTS.get(re.match(r"https?://[^/]+", url).group(0))
    d = rp.crawl_delay(UA) if rp else None
    return max(float(d or 0), default)


def _country(name):
    n = (name or "").strip()
    return COUNTRY_ISO.get(n.lower(), n or None)


def _div(cat):
    return {"Men's Bodybuilding": "Bodybuilding", "Women's Fit Model": "Fit Model"}.get(cat, cat)


# ---------------------------------------------------------------- npcnewsonline (NPC Worldwide)
def _stec_events(start, end):
    url = f"{NPCNEWS}/wp-json/stec/v2/get/calendars/{STEC_CAL_DEFAULT}/events/{start}/{end}"
    if not allowed(url):
        return []
    try:
        d = json.loads(get(url, headers={"Accept": "application/json"}))
    except Exception as e:  # noqa: BLE001
        log(f"  ! npcnewsonline {start}~{end}: {e}")
        return []
    return (d.get("data") or {}).get("events") or []


def _npc_events(years):
    out, seen = [], set()
    today = datetime.now(KST).strftime("%Y-%m-%d")
    for y in years:
        for e in _stec_events(f"{y}-01-01", f"{y}-12-31"):
            if e.get("id") in seen or e.get("post_status") != "publish":
                continue
            seen.add(e.get("id"))
            cats = [c.get("title") for c in e.get("category") or []]
            if "NPC Worldwide" in cats:
                fed = "NPC WW"
            elif INCLUDE_NPC_USA and "National Physique Committee" in cats:
                fed = "NPC"
            else:
                continue
            title = html.unescape(e.get("title") or "").strip()
            name = re.sub(r"^\d{4}\s+", "", title)
            name = re.sub(r"^NPC\s+(Worldwide\s+)?", "", name).strip() or title
            date = (e.get("start_date") or "")[:10]
            if not re.match(r"\d{4}-\d\d-\d\d$", date):
                continue
            end = (e.get("end_date") or "")[:10]
            loc = (e.get("location") or {}).get("full_address") or (e.get("location") or {}).get("address") or ""
            parts = [p.strip() for p in loc.split(",") if p.strip()]
            country = _country(parts[-1]) if len(parts) >= 2 else ("US" if fed == "NPC" else None)
            if fed == "NPC" and len(parts) == 2 and re.fullmatch(r"[A-Z]{2}", parts[-1]):
                country = "US"  # 'Columbus, OH'
            desc = e.get("description") or ""
            reg = re.search(r'href="([^"]+)"[^>]*>\s*Athlete Registration', desc)
            cancelled = bool(re.search(r"CANCEL", html.unescape(re.sub(r"<[^>]+>", "", desc)), re.I)) \
                or e.get("event_status") in ("EventCancelled", "EventPostponed")
            orgs = ", ".join(o.get("name") for o in e.get("organizers") or [] if o.get("name"))
            divisions = [_div(c) for c in cats if c and c not in NON_DIVISION_CATS]
            tags = [c for c in cats if c in ("Natural",)]
            ev = {
                "id": f"ifbbpro_world-npc-{e.get('id')}",
                "src": SOURCE["key"], "fed": fed, "name": name,
                "date": date, "end": end if end and end > date else None,
                "city": ", ".join(parts[:-1]) if len(parts) >= 2 else (parts[0] if parts else None),
                "country": country,
                "divisions": divisions or None,
                "natural": True if tags or re.search(r"natural", title, re.I) else None,
                "host": orgs or None,
                "website": (e.get("link") or {}).get("url") or None,
                "url": e.get("permalink"),
                "regUrl": html.unescape(reg.group(1)).replace(" ", "") if reg else None,
                "tier": "national" if country == "KR" else "international",
                "major": bool(re.search(r"pro qualifier|amateur olympia|olympia amateur", title, re.I)),
                "closed": bool(cancelled or (end or date) < today) or None,
                "cancelled": cancelled or None,
            }
            out.append({k: v for k, v in ev.items() if v is not None})
    return out


# ---------------------------------------------------------------- ifbbpro.com (IFBB Pro League)
def _challenge(body):
    return "One moment, please" in body[:3000] or "request is being verified" in body[:5000]


def _ifbbpro_shows(years):
    """ifbbpro.com 일정 — The Events Calendar REST 를 시도. 봇 검증 페이지면 빈 목록."""
    url = (f"{IFBBPRO}/wp-json/tribe/events/v1/events?per_page=50"
           f"&start_date={min(years)}-01-01&end_date={max(years)}-12-31")
    if not allowed(url):
        return []
    delay = _crawl_delay(url, IFBBPRO_DELAY)
    out, page = [], 0
    while url and page < 20:
        page += 1
        try:
            body = get(url, headers={"Accept": "application/json"}, delay=delay)
        except Exception as e:  # noqa: BLE001
            log(f"  ! ifbbpro.com: {e}")
            break
        if _challenge(body):
            log("  ! ifbbpro.com: 봇 검증 페이지가 반환됨 — IFBB 프로쇼 일정은 건너뜀")
            break
        try:
            d = json.loads(body)
        except ValueError:
            log("  ! ifbbpro.com: JSON 아님 — 건너뜀")
            break
        for e in d.get("events") or []:
            v = e.get("venue") or {}
            v = v if isinstance(v, dict) else {}
            city = ", ".join(x for x in (v.get("city"), v.get("state") or v.get("province")) if x)
            country = _country(v.get("country"))
            st = (v.get("state") or v.get("province") or "").strip()
            if not country and re.fullmatch(r"[A-Z]{2}", st or ""):
                country = "US"  # 미국 주 약어만 있고 국가가 비어 있는 경우
            date = (e.get("start_date") or "")[:10]
            end = (e.get("end_date") or "")[:10]
            cats = [c.get("name") for c in (e.get("categories") or []) + (e.get("tags") or []) if c.get("name")]
            ev = {
                "id": f"ifbbpro_world-pro-{e.get('id')}", "src": SOURCE["key"], "fed": "IFBB PRO",
                "name": html.unescape(re.sub(r"<[^>]+>", "", e.get("title") or "")).strip(),
                "date": date, "end": end if end > date else None,
                "place": html.unescape(v.get("venue") or "") or None, "city": city or None,
                "country": country or None,
                "divisions": [c for c in cats if re.search(r"physique|bikini|figure|fitness|wellness|bodybuilding|fit model|212", c, re.I)] or None,
                "url": e.get("url"), "tier": "national" if country == "KR" else "international",
                "major": bool(re.search(r"olympia|arnold classic", e.get("title") or "", re.I)) and not re.search(r"amateur", e.get("title") or "", re.I),
            }
            if date:
                out.append({k: v for k, v in ev.items() if v is not None})
        url = d.get("next_rest_url")
    return out


def crawl():
    y = this_year()
    years = [y, y + 1]
    pro = _ifbbpro_shows(years)
    npc = _npc_events(years)
    log(f"  ifbbpro_world: IFBB PRO {len(pro)}개, NPC {len(npc)}개")
    events = pro + npc
    events.sort(key=lambda e: (e["date"], e["name"]))
    return events
