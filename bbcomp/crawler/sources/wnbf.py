"""WNBF (World Natural Bodybuilding Federation) — https://worldnaturalbb.com/international-events/

주의: 2026-11 현재 이 사이트는 Cloudflare 챌린지(HTTP 403, cf-mitigated: challenge)로
일반 요청을 막는다. 우회하지 않고, 403이면 로그만 남기고 []를 반환한다.
페이지가 열릴 때를 대비한 파서는 실제 HTML을 보지 못한 상태의 범용 텍스트 파서다
(제목 줄 + 'Month D(-D), YYYY' 날짜 줄 + 장소 줄). 열리면 실제 구조에 맞게 다듬을 것.
"""
import re
import urllib.error

from .common import get, iso, log, text

BASE = "https://worldnaturalbb.com"
SOURCE = {"key": "wnbf", "label": "WNBF", "url": f"{BASE}/international-events/"}

MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"])}
MON = r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE = re.compile(MON + r"\.?\s+(\d{1,2})(?:\s*[-–]\s*(?:" + MON + r"\.?\s+)?(\d{1,2}))?,?\s+(20\d\d)", re.I)
COUNTRIES = [
    (r"Korea|Seoul|Jeongseon|High1|정선", "KR"), (r"USA|United States|, [A-Z]{2}\b", "US"),
    (r"Canada", "CA"), (r"Australia", "AU"), (r"United Kingdom|England|UK\b", "GB"), (r"Ireland", "IE"),
    (r"Japan", "JP"), (r"China", "CN"), (r"Taiwan", "TW"), (r"Brazil", "BR"), (r"Italy", "IT"),
    (r"Germany", "DE"), (r"France", "FR"), (r"Netherlands", "NL"), (r"Spain", "ES"), (r"India", "IN"),
    (r"Philippines", "PH"), (r"Thailand", "TH"), (r"Mexico", "MX"), (r"New Zealand", "NZ"),
]


def _mon(s):
    s = s.lower()[:3]
    return next(v for k, v in MONTHS.items() if k.startswith(s))


def _country(s):
    for pat, cc in COUNTRIES:
        if re.search(pat, s or "", re.I):
            return cc
    return None


def _parse(t, url):
    lines = [x.strip() for x in t.split("\n") if x.strip()]
    events = {}
    for i, ln in enumerate(lines):
        m = DATE.search(ln)
        if not m:
            continue
        y = int(m.group(5))
        start = iso(y, _mon(m.group(1)), m.group(2))
        end = iso(y, _mon(m.group(3) or m.group(1)), m.group(4)) if m.group(4) else None
        # 제목: 같은 줄의 날짜 앞부분, 없으면 바로 위 줄
        name = ln[:m.start()].strip(" -–|:") or (lines[i - 1] if i else "")
        if not re.search(r"WNBF|Natural|Championship|Pro|Open|Classic|Universe|World", name, re.I):
            continue
        place = ln[m.end():].strip(" -–|:,") or (lines[i + 1] if i + 1 < len(lines) else "")
        if DATE.search(place):
            place = ""
        cc = _country(" ".join([name, place]))
        key = re.sub(r"[^a-z0-9]+", "-", f"{name}-{start}".lower()).strip("-")[:80]
        events[key] = {
            "id": f"wnbf-{key}", "src": "wnbf", "fed": "WNBF", "name": name,
            "date": start, "end": end if end and end > start else None,
            "place": place or None, "city": None, "country": cc or None,
            "fee": None, "deadline": None, "divisions": [], "host": "WNBF",
            "url": url, "regUrl": None,
            "tier": "national" if cc == "KR" else "international",
            "major": bool(re.search(r"Pro|World|Universe|International", name, re.I)),
        }
    return list(events.values())


def crawl():
    try:
        page = get(SOURCE["url"])
    except urllib.error.HTTPError as e:
        log(f"  ! wnbf {e.code} — 사이트가 자동 요청을 차단(Cloudflare). 건너뜀")
        return []
    except Exception as e:  # noqa: BLE001
        log(f"  ! wnbf 실패: {e}")
        return []
    events = _parse(text(page), SOURCE["url"])
    # 한국 WNBF 페이지가 링크돼 있으면 함께 읽는다
    for link in sorted(set(re.findall(r'href="(https?://[^"]*korea[^"]*)"', page, re.I)))[:3]:
        try:
            events += _parse(text(get(link)), link)
        except Exception as e:  # noqa: BLE001
            log(f"  ! wnbf 한국 페이지 실패 {link}: {e}")
    seen, out = set(), []
    for e in sorted(events, key=lambda e: e["date"]):
        if e["id"] not in seen:
            seen.add(e["id"])
            out.append(e)
    return out
