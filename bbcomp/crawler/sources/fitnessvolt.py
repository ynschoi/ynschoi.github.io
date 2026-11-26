"""IFBB 프로 리그 프로쇼 일정 — fitnessvolt.com (비공식 일정·결과 모음)

공식 사이트(ifbbpro.com)는 봇 확인 화면으로 막혀 있어 이 사이트를 대신 쓴다. 앱에는 '비공식 출처'로 표시.
사이트 부담을 줄이기 위해:
  - 매주: 시즌 페이지 1회 + 일정 페이지 1회 (예정 대회의 날짜·종목은 일정 페이지 표에서)
  - 대회 상세 페이지는 data.json에 아직 없는 대회만 1초 간격으로 1회씩 (이후 주에는 새 대회만)
"""
import html
import json
import os
import re
from datetime import datetime

from .common import get, log, text, this_year

BASE = "https://fitnessvolt.com/bodybuilding"
SOURCE = {"key": "fitnessvolt", "label": "IFBB 프로쇼 (fitnessvolt.com · 비공식 모음)",
          "url": f"{BASE}/schedule/ifbb-pro/"}
UA = {"User-Agent": "Mozilla/5.0 (compatible; bbcomp-schedule-bot/1.0; weekly personal schedule page)"}
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data.json")
MAX_NEW_DETAILS = 260

COUNTRY = {"United States": "US", "South Korea": "KR", "Japan": "JP", "China": "CN", "Taiwan": "TW", "Thailand": "TH",
           "Spain": "ES", "Portugal": "PT", "Brazil": "BR", "Canada": "CA", "Mexico": "MX", "United Kingdom": "GB",
           "Germany": "DE", "Italy": "IT", "France": "FR", "Australia": "AU", "India": "IN", "Philippines": "PH",
           "Romania": "RO", "Poland": "PL", "Argentina": "AR", "Austria": "AT", "Saudi Arabia": "SA",
           "South Africa": "ZA", "Tunisia": "TN", "Mongolia": "MN", "Vietnam": "VN", "Indonesia": "ID",
           "Malaysia": "MY", "Singapore": "SG", "Hong Kong": "HK", "UAE": "AE", "United Arab Emirates": "AE"}


def _date(s):
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _loc(loc):
    parts = [p.strip() for p in (loc or "").split(",") if p.strip()]
    country = parts[-1] if parts else None
    city = ", ".join(parts[:-1]) if len(parts) > 1 else None
    return city, COUNTRY.get(country, country)


def _event(slug, name, date, loc, divisions, place=None, done=False):
    city, country = _loc(loc)
    name = re.sub(r"^\s*20\d\d\s+", "", html.unescape(name)).strip()
    top = bool(re.search(r"\bolympia\b|arnold classic", name, re.I)) and "amateur" not in name.lower()
    return {
        "id": f"fitnessvolt-{slug}", "fed": "IFBB PRO", "name": name, "date": date,
        "place": place if place and place != city else None, "city": city, "country": country or "?",
        "divisions": divisions, "url": f"{BASE}/contests/{slug}/",
        "tier": "national" if country == "KR" else "international",
        "major": top, "closed": done, "unofficial": True,
    }


def crawl():
    known = {}
    try:
        with open(DATA, encoding="utf-8") as f:
            known = {e["id"]: e for e in json.load(f).get("events", []) if e.get("src") == "fitnessvolt"}
    except Exception:  # noqa: BLE001
        pass

    events = {}
    # 1) 일정 페이지: 예정 + 최근 2주 대회 (날짜·종목 포함)
    sched = get(SOURCE["url"], headers=UA)
    for row in re.findall(r"<tr>\s*<td data-label=\"Date\">.*?</tr>", sched, re.S):
        m_d = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})"', row)
        m_a = re.search(r'/contests/([^/"]+)/"[^>]*>(.*?)</a>', row, re.S)
        if not (m_d and m_a):
            continue
        cell = lambda k: text((re.search(r'data-label="%s"[^>]*>(.*?)</td>' % k, row, re.S) or [None, ""])[1])  # noqa: E731
        divs = [d.strip() for d in cell("Divisions").split(",") if d.strip() and "lineup" not in d.lower()]
        done = "result" in cell("Status").lower()
        events[m_a.group(1)] = _event(m_a.group(1), text(m_a.group(2)), m_d.group(1), cell("Location"), divs, done=done)

    # 2) 시즌 페이지: 전체 대회 목록 (날짜는 상세 페이지에만 있음)
    todo = []
    for year in (this_year(), this_year() + 1):
        try:
            season = get(f"{BASE}/seasons/{year}/", headers=UA)
        except Exception as e:  # noqa: BLE001
            log(f"  fitnessvolt {year} 시즌 없음 ({e})")
            continue
        for row in re.findall(r"<tr>\s*<td data-label=\"Date\">.*?</tr>", season, re.S):
            m_a = re.search(r'/contests/([^/"]+)/"[^>]*>(.*?)</a>', row, re.S)
            if not m_a or m_a.group(1) in events:
                continue
            slug = m_a.group(1)
            if f"fitnessvolt-{slug}" in known:
                events[slug] = dict(known[f"fitnessvolt-{slug}"])
                continue
            if "unconfirmed" in row.lower():
                continue  # 날짜 미확정 → 일정 페이지에 뜨면 그때 수집
            todo.append((slug, text(m_a.group(2))))
    log(f"  fitnessvolt 일정표 {len(events)}건, 새 상세 {len(todo)}건")

    # 3) 새 대회만 상세 페이지 1회
    for slug, name in todo[:MAX_NEW_DETAILS]:
        try:
            p = get(f"{BASE}/contests/{slug}/", headers=UA, delay=1.0)
        except Exception as e:  # noqa: BLE001
            log(f"  ! {slug}: {e}")
            continue
        fact = lambda k: text((re.search(r'<dt class="bb-eyebrow">%s</dt>\s*<dd[^>]*>(.*?)</dd>' % k, p, re.S) or [None, ""])[1])  # noqa: E731
        date = _date(fact("Date"))
        if not date:
            continue
        divs = []
        m_t = re.search(r"Results by Division</h2>(.*?)</table>", p, re.S)
        if m_t:
            for tr in re.findall(r"<tr>\s*<td>(.*?)</td>", m_t.group(1), re.S):
                d = text(tr)
                if d and d not in divs:
                    divs.append(d)
        events[slug] = _event(slug, name, date, fact("Location"), divs, place=fact("Venue") or None, done=True)
    return list(events.values())
