"""운동의모든것 (WNGP·MUSA·ANBC·BOB) — https://unmo.kr/m/shop/tournament.php

목록에 연간 전체 대회(종료 포함)가 있고, 상세(tm_view.php)에 일자·장소·출전비·주최,
종목 선택 옵션이 있다. 접수 마감은 목록의 카운트다운 시각에서 읽는다.
"""
import re
from datetime import datetime, timedelta

from .common import get, log, parse_kdate, text, this_year

BASE = "https://unmo.kr"
SOURCE = {"key": "unmo", "label": "운동의모든것 (WNGP·MUSA·ANBC·BOB)", "url": f"{BASE}/m/shop/tournament.php"}
FEDS = ["WNGP", "MUSA", "ANBC", "BOB"]
SKIP = ["세미나", "설명회", "입장권", "추가 접수", "추가접수"]


def _field(page, label):
    m = re.search(r"<li class='tlst[^']*'>\s*" + re.escape(label) + r"\s*</li>\s*<li class='trst[^']*'>(.*?)</li>",
                  page, re.S)
    return text(m.group(1)) if m else ""


def _divisions(page):
    m = re.search(r'<select id="it_option_1"[^>]*>(.*?)</select>', page, re.S)
    if not m:
        return []
    out = []
    for o in re.findall(r"<option[^>]*>(.*?)</option>", m.group(1), re.S):
        o = text(o)
        if not o or "선택" in o or set(o) <= set("-— "):
            continue
        if o not in out:
            out.append(o)
    return out


def _deadline(countdown):
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})\s*([AP]M)?", countdown or "", re.I)
    if not m:  # 사이트 표기가 '00:00 AM'처럼 12시간제와 섞여 있어 직접 해석
        return None
    mo, d, y, hh, mi, ap = m.groups()
    hh = int(hh) % 12 + (12 if (ap or "").upper() == "PM" else 0)
    dt = datetime(int(y), int(mo), int(d), hh, int(mi))
    if hh == 0 and int(mi) == 0:
        dt -= timedelta(days=1)
    return dt.strftime("%Y-%m-%d")


def crawl():
    items, page = [], 1
    while page <= 30:
        body = get(SOURCE["url"], {"page": page})
        found = []
        for li in re.findall(r"<li>\s*<a href=\"[^\"]*tm_view\.php.*?</li>", body, re.S):
            m_id = re.search(r"gs_id=(\d+)", li)
            m_nm = re.search(r'<dd class="pname">(.*?)</dd>', li, re.S)
            m_cd = re.search(r'CountDownTimer\("([^"]+)"', li)
            if m_id and m_nm and m_id.group(1) not in {i[0] for i in items}:
                found.append((m_id.group(1), m_nm.group(1), m_cd.group(1) if m_cd else ""))
        if not found:
            break
        items += found
        page += 1
    log(f"  unmo 목록 {len(items)}건")

    events = []
    for gid, raw_name, countdown in items:
        name = text(raw_name)
        ended = "[대회종료]" in name
        name = name.replace("[대회종료]", "").strip()
        if any(w in name for w in SKIP):
            continue
        url = f"{BASE}/m/shop/tm_view.php?gs_id={gid}"
        try:
            p = get(url)
        except Exception as e:  # noqa: BLE001
            log(f"  ! 상세 실패 {gid}: {e}")
            continue
        start, end = parse_kdate(_field(p, "대회 일자"), this_year())
        if not start:
            log(f"  - 날짜 없음, 건너뜀: {name} ({gid})")
            continue
        fed = next((f for f in FEDS if re.search(f, name, re.I)), "기타")
        short = re.sub(r"^\s*" + re.escape(fed) + r"\s*", "", name, flags=re.I).strip() or name
        place = _field(p, "대회 장소")
        overseas = re.search(r"일본|몽골|홍콩|중국|태국|필리핀|베트남|대만", name)
        events.append({
            "id": f"unmo-{gid}", "src": "unmo", "fed": fed, "name": short,
            "date": start, "end": end,
            "place": None if (not place or "추후" in place) else place,
            "country": "KR" if not overseas else overseas.group(0),
            "fee": (_field(p, "대회 출전비").replace(" 원", "원") or None),
            "deadline": _deadline(countdown), "divisions": _divisions(p),
            "host": _field(p, "대회 주최") or None, "url": url, "regUrl": url,
            "tier": "international" if overseas else "national",
            "major": bool(re.search(r"파이널|챔피언|프로전", name)), "closed": ended,
        })
    return events
