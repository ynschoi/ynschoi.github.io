#!/usr/bin/env python3
"""보디빌딩 대회일정 크롤러 → bbcomp/data.json

소스
  - unmo   : 운동의모든것 (WNGP·MUSA·ANBC·BOB)  https://unmo.kr/m/shop/tournament.php
             연간 전체 대회(종료 포함)가 목록에 있고, 상세에 일자·장소·출전비가 있음
  - coachn : 코치엔 (PCA·NPCA)                  https://coachn.co.kr/sub/competitions_list.php
             '현재 접수 회차'만 노출 → 한 번 본 대회는 data.json에 누적 보관
  - manual : bbcomp/crawler/manual.json  크롤링 가능한 공식 사이트를 아직 못 찾은 연맹(수동 입력)

규칙
  - 소스가 실패하거나 0건이면 그 소스의 기존 데이터를 그대로 유지(앱이 비지 않도록)
  - 표준 라이브러리만 사용 (GitHub Actions에서 pip 설치 불필요)
사용: python3 bbcomp/crawler/crawl.py [--out bbcomp/data.json]
"""
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "..", "data.json")
DELAY = 0.4  # 요청 간 간격(초) — 사이트 부담 최소화


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def get(url, params=None, tries=3):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko"})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode("utf-8", errors="replace")
            time.sleep(DELAY)
            return body
        except Exception as e:  # noqa: BLE001
            wait = 5 * (2 ** i)
            log(f"  ! {url} ({e}) — {wait}s 후 재시도")
            time.sleep(wait)
    raise RuntimeError(f"요청 실패: {url}")


def text(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def iso(y, m, d):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


# ───────────────────────── 운동의모든것 ─────────────────────────
UNMO = "https://unmo.kr"
UNMO_FEDS = ["WNGP", "MUSA", "ANBC", "BOB"]
SKIP_WORDS = ["세미나", "설명회", "입장권", "추가 접수", "추가접수"]


def unmo_fed(name):
    found = [f for f in UNMO_FEDS if re.search(f, name, re.I)]
    if not found:
        return "기타"
    return found[0]


def unmo_detail_field(page, label):
    m = re.search(r"<li class='tlst[^']*'>\s*" + re.escape(label) + r"\s*</li>\s*<li class='trst[^']*'>(.*?)</li>",
                  page, re.S)
    return text(m.group(1)) if m else ""


def parse_kdate(s, year_hint):
    """'2026년 12월 5일 토요일', '2026년 8월 15일 ~ 16일', '2026년 8월 15일~8월 16일' → (start, end)"""
    m = re.search(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", s)  # '2026-12-12 토요일'
    if m:
        start = iso(*m.groups())
        m2 = re.search(r"[~\-–]\s*(?:(\d{4})[-./])?(?:(\d{1,2})[-./])?(\d{1,2})\b", s[m.end():])
        end = iso(m2.group(1) or m.group(1), m2.group(2) or m.group(2), m2.group(3)) if m2 else None
        return start, (end if end and end > start else None)
    m = re.search(r"(?:(\d{4})\s*년\s*)?(\d{1,2})\s*월\s*(\d{1,2})\s*일", s)
    if not m:
        return None, None
    y = int(m.group(1) or year_hint)
    start = iso(y, m.group(2), m.group(3))
    rest = s[m.end():]
    m2 = re.search(r"[~\-–]\s*(?:(\d{1,2})\s*월\s*)?(\d{1,2})\s*일", rest)
    end = iso(y, m2.group(1) or m.group(2), m2.group(2)) if m2 else None
    return start, (end if end and end > start else None)


def crawl_unmo():
    items, page = [], 1
    while True:
        body = get(f"{UNMO}/m/shop/tournament.php", {"page": page})
        found = []
        for li in re.findall(r"<li>\s*<a href=\"[^\"]*tm_view\.php.*?</li>", body, re.S):
            m_id = re.search(r"gs_id=(\d+)", li)
            m_nm = re.search(r'<dd class="pname">(.*?)</dd>', li, re.S)
            m_cd = re.search(r'CountDownTimer\("([^"]+)"', li)
            if m_id and m_nm:
                found.append((m_id.group(1), m_nm.group(1), m_cd.group(1) if m_cd else ""))
        new = [f for f in found if f[0] not in {i[0] for i in items}]
        if not new:
            break
        items += new
        log(f"  unmo 목록 {page}페이지: {len(new)}건")
        page += 1
        if page > 30:
            break
    year_now = datetime.now(KST).year
    events = []
    for gid, raw_name, countdown in items:
        name = text(raw_name)
        ended = "[대회종료]" in name
        name = name.replace("[대회종료]", "").strip()
        if any(w in name for w in SKIP_WORDS):
            continue
        url = f"{UNMO}/m/shop/tm_view.php?gs_id={gid}"
        try:
            page_html = get(url)
        except RuntimeError as e:
            log(f"  ! 상세 실패 {gid}: {e}")
            continue
        start, end = parse_kdate(unmo_detail_field(page_html, "대회 일자"), year_now)
        if not start:
            log(f"  - 날짜 없음, 건너뜀: {name} ({gid})")
            continue
        fee = unmo_detail_field(page_html, "대회 출전비").replace(" 원", "원")
        place = unmo_detail_field(page_html, "대회 장소")
        host = unmo_detail_field(page_html, "대회 주최")
        deadline = None
        if countdown:  # "11/30/2026 00:00 AM" → 11/29까지 접수
            m_cd = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})\s*([AP]M)?", countdown, re.I)
            if m_cd:  # 사이트 표기가 '00:00 AM'처럼 12시간제와 섞여 있어 직접 해석
                mo, d, y, hh, mi, ap = m_cd.groups()
                hh = int(hh) % 12 + (12 if (ap or "").upper() == "PM" else 0)
                dt = datetime(int(y), int(mo), int(d), hh, int(mi))
                if hh == 0 and int(mi) == 0:
                    dt -= timedelta(days=1)
                deadline = dt.strftime("%Y-%m-%d")
        fed = unmo_fed(name)
        short = re.sub(r"^\s*" + re.escape(fed) + r"\s*", "", name, flags=re.I).strip() or name
        events.append({
            "id": f"unmo-{gid}", "src": "unmo", "fed": fed, "name": short,
            "date": start, "end": end, "place": place or None, "fee": fee or None,
            "deadline": deadline, "host": host or None, "url": url,
            "major": bool(re.search(r"파이널|챔피언", name)), "closed": ended,
        })
    return events


# ───────────────────────── 코치엔 (PCA·NPCA) ─────────────────────────
COACHN = "https://coachn.co.kr"
COACHN_CATS = {"PCA접수": "PCA", "NPCA접수": "NPCA", "NPCA뉴빅터접수": "NPCA"}


def crawl_coachn():
    year_now = datetime.now(KST).year
    events = []
    for sca, fed in COACHN_CATS.items():
        body = get(f"{COACHN}/sub/competitions_list.php", {"sca": sca})
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
            name = re.sub(r"^" + fed + r"\s+", "", name).strip()
            events.append({
                "id": f"coachn-{m_id.group(1)}", "src": "coachn", "fed": fed, "name": name,
                "date": start, "end": end, "place": None,
                "fee": f"{m_fee.group(1)}원" if m_fee else None, "deadline": None,
                "status": status or None, "host": "PCA KOREA",
                "url": f"{COACHN}/sub/competitions_list.php?sca={urllib.parse.quote(sca)}",
                "major": bool(re.search(r"CHAMPIONSHIP|챔피언|FINAL|파이널", title, re.I)),
            })
        log(f"  coachn {sca}: 누적 {len(events)}건")
    return events


SOURCES = {
    "unmo": {"label": "운동의모든것 (WNGP·MUSA·ANBC·BOB)", "url": f"{UNMO}/m/shop/tournament.php",
             "fn": crawl_unmo, "accumulate": False},
    "coachn": {"label": "코치엔 (PCA·NPCA)", "url": f"{COACHN}/sub/competitions_list.php",
               "fn": crawl_coachn, "accumulate": True},
}


def main():
    out = DEFAULT_OUT
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    out = os.path.abspath(out)
    only = [a for a in sys.argv[1:] if a in SOURCES]

    old = {"events": [], "sources": {}}
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            old = json.load(f)
    old_by_src = {}
    for e in old.get("events", []):
        old_by_src.setdefault(e.get("src"), []).append(e)

    now = datetime.now(KST).isoformat(timespec="minutes")
    events, sources = [], dict(old.get("sources", {}))
    for key, s in SOURCES.items():
        prev = old_by_src.get(key, [])
        if only and key not in only:
            events += prev
            continue
        log(f"[{key}] 수집 시작")
        try:
            got = s["fn"]()
        except Exception as e:  # noqa: BLE001
            log(f"[{key}] 실패: {e}")
            got = []
        if got:
            if s["accumulate"]:
                ids = {e["id"] for e in got}
                got += [e for e in prev if e["id"] not in ids]
            events += got
            sources[key] = {"label": s["label"], "url": s["url"], "ok": True, "count": len(got), "checked": now,
                            "updated": now}
        else:
            events += prev
            sources[key] = {**sources.get(key, {}), "label": s["label"], "url": s["url"], "ok": False,
                            "count": len(prev), "checked": now}
        log(f"[{key}] {'성공' if got else '실패/0건 — 기존 데이터 유지'}: {sources[key]['count']}건")

    # 수동 입력(크롤링 대상이 아닌 연맹). 같은 연맹·같은 날 크롤링 데이터가 있으면 수동 항목은 제외
    manual_path = os.path.join(HERE, "manual.json")
    if os.path.exists(manual_path):
        with open(manual_path, encoding="utf-8") as f:
            manual = json.load(f)
        have = {(e["fed"], e["date"]) for e in events}
        covered = {"WNGP", "MUSA", "ANBC", "BOB"}  # unmo가 연간 전체를 주는 연맹 → 수동 항목 불필요
        kept = [dict(e, src="manual") for e in manual.get("events", [])
                if (e["fed"], e["date"]) not in have and e["fed"] not in covered]
        events += kept
        sources["manual"] = {"label": manual.get("label", "수동 입력"), "url": None, "ok": True,
                             "count": len(kept), "checked": now, "updated": manual.get("updated")}

    events.sort(key=lambda e: (e["date"], e["fed"], e["name"]))
    data = {"generated": now, "sources": sources, "events": events}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    log(f"저장: {out} ({len(events)}건)")
    if not any(s.get("ok") for k, s in sources.items() if k != "manual"):
        sys.exit(1)  # 모든 크롤러 실패 → 워크플로를 실패로 표시해 알림


if __name__ == "__main__":
    main()
