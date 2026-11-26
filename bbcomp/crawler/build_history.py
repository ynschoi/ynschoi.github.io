#!/usr/bin/env python3
"""지난해(기본 2025) 국내 보디빌딩 대회 일정 스냅샷 → bbcomp/history/<YEAR>.json

앱의 '지난해 이맘때 이런 대회가 있었다' 표시용 1회성 스냅샷. 매주 크롤러(crawl.py)와 별개로 필요할 때 손으로 다시 돌린다.
한국 개최(country=KR) 대회 위주. 사이트당 한 번에 한 요청, robots.txt 확인, 403·봇 확인·로그인은 우회하지 않고 건너뛴다.

출처 (2026-11 확인)
  1) npcnewsonline.com  NPC Worldwide 캘린더 REST (stec) — 몬스터짐 코리아 리저널·프로 퀄리파이어
  2) fitnessvolt.com     2025 시즌 페이지에서 한국 개최 프로쇼만 골라 상세 페이지(1초 간격)에서 날짜
  3) unmo.kr             WNGP·MUSA·ANBC·BOB. 목록에는 올해 대회만 남아 있지만 지난 대회 상세(tm_view.php?gs_id=N)는
                         공개 상태로 남아 있어, 목록의 가장 큰 ID부터 아래로 1초 간격으로 훑는다
                         (연도가 YEAR 미만인 상세가 연속 STOP_RUN 건이면 중단)
  4) coachn.co.kr        PCA·NPCA 매거진 중 'YEAR' 제목 글의 본문 날짜 문장
  5) afex.co.kr          홈에 남아 있는 지난 회차 안내(일시·장소)
  6) fitschedule.co.kr   /competitions 의 RSC 페이로드 "competitions":[...] 중 YEAR 날짜 (2026-11 현재 0건)
  7) physiquehub.kr      sitemap 의 /competitions/YEAR-... 상세 (2026-11 현재 0건)
  확인만 하고 못 쓴 곳: zerotohero.co.kr(403), bodybuilding.or.kr(KBBF, 이 환경 403), ifbbprokorea.com(지난 시즌 일정 없음)

사용: python3 bbcomp/crawler/build_history.py [--year 2025] [--out path]
"""
import difflib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sources.common import KST, get, log, parse_kdate, text  # noqa: E402

YEAR = 2025
FEDS = {"PCA", "NPCA", "WNGP", "MUSA", "ANBC", "BOB", "NPC", "AGP", "IFBB PRO", "NABBA", "AFEX", "AGONAS",
        "케이클래식", "ONECLASSIC", "NAC", "ICN", "WNBF", "MUSCLEMANIA", "KBBF", "WNC", "몬스터짐", "기타"}
BOT_UA = {"User-Agent": "Mozilla/5.0 (compatible; bbcomp-schedule-bot/1.0; personal schedule page)"}
OVERSEAS = {"일본": "JP", "몽골": "MN", "홍콩": "HK", "중국": "CN", "태국": "TH", "필리핀": "PH", "베트남": "VN",
            "대만": "TW", "마카오": "MO", "말레이시아": "MY", "싱가포르": "SG", "인도네시아": "ID"}

SOURCES = {
    "npcnews": ("NPC Worldwide 캘린더 (npcnewsonline.com)", "https://npcnewsonline.com/schedule/"),
    "fitnessvolt": ("IFBB 프로쇼 (fitnessvolt.com · 비공식)", "https://fitnessvolt.com/bodybuilding/seasons/{y}/"),
    "unmo": ("운동의모든것 (unmo.kr)", "https://unmo.kr/m/shop/tournament.php"),
    "coachn": ("PCA·NPCA 매거진 (coachn.co.kr)", "https://coachn.co.kr/bbs/board.php?bo_table=magazine"),
    "afex": ("AFEX KOREA (afex.co.kr)", "https://www.afex.co.kr/"),
    "fitschedule": ("핏스케줄 (fitschedule.co.kr · 비공식)", "https://fitschedule.co.kr/competitions"),
    "physiquehub": ("피지크허브 (physiquehub.kr · 비공식)", "https://physiquehub.kr/competitions"),
}
NOTES = []


def note(msg):
    NOTES.append(msg)
    log("  ! " + msg)


def fetch(url, **kw):
    """get() 래퍼: 403/404/robots 금지 등은 None (우회하지 않음)."""
    try:
        return get(url, **kw)
    except urllib.error.HTTPError as e:
        note(f"{url} → HTTP {e.code}, 건너뜀")
    except Exception as e:  # noqa: BLE001
        note(f"{url} → {str(e)[:120]}, 건너뜀")
    return None


def ev(key, slug, fed, name, date, end=None, place=None, city=None, country="KR", url=None):
    assert fed in FEDS, fed
    slug = re.sub(r"[^0-9a-z가-힣]+", "-", slug.lower()).strip("-")
    return {"id": f"h{YEAR}-{key}-{slug}", "fed": fed, "name": name.strip(), "date": date,
            "end": end if end and end > date else None, "place": place or None, "city": city or None,
            "country": country or "KR", "src": SOURCES[key][0], "url": url}


# ---------------------------------------------------------------- 1) npcnewsonline (몬스터짐)
def npcnews():
    url = f"https://npcnewsonline.com/wp-json/stec/v2/get/calendars/686587/events/{YEAR}-01-01/{YEAR}-12-31"
    body = fetch(url, headers={"Accept": "application/json"})
    if not body:
        return []
    out = []
    for e in (json.loads(body).get("data") or {}).get("events") or []:
        title = html.unescape(e.get("title") or "").strip()
        loc = (e.get("location") or {}).get("full_address") or ""
        if e.get("post_status") != "publish" or not re.search(r"korea", loc, re.I):
            continue
        date, end = (e.get("start_date") or "")[:10], (e.get("end_date") or "")[:10]
        if not date.startswith(str(YEAR)):
            continue
        n = re.sub(r"^\d{4}\s+NPC\s+(Worldwide\s+)?", "", title)
        mz = re.search(r"monsterzym", n, re.I)
        kind = n.lower()
        ko = kind
        for en, k in [("world of monsterzym", "월드 오브 몬스터짐"), ("monsterzym", "몬스터짐"), ("korea", "코리아"),
                      ("natural pro qualifier", "내추럴 프로 퀄리파이어"), ("open pro qualifier", "오픈 프로 퀄리파이어"),
                      ("pro qualifier", "프로 퀄리파이어"), ("natural regional", "내추럴 리저널"),
                      ("open regional", "오픈 리저널")]:
            ko = ko.replace(en, k)
        name = re.sub(r"\s+", " ", ko).strip() if mz and not re.search(r"[a-z]{3,}", ko) else n
        parts = [p.strip() for p in loc.split(",") if p.strip()]
        out.append(ev("npcnews", str(e.get("id")), "몬스터짐" if mz else "NPC", name, date, end,
                      city=parts[0] if len(parts) >= 2 else None, url=e.get("permalink")))
    return out


# ---------------------------------------------------------------- 2) fitnessvolt (국내 프로쇼)
def fitnessvolt():
    base = "https://fitnessvolt.com/bodybuilding"
    season = fetch(f"{base}/seasons/{YEAR}/", headers=BOT_UA)
    if not season:
        return []
    out = []
    for row in re.findall(r"<tr>\s*<td data-label=\"Date\">.*?</tr>", season, re.S):
        m = re.search(r'/contests/([^/"]+)/"[^>]*>(.*?)</a>', row, re.S)
        loc = text((re.search(r'data-label="Location">(.*?)</td>', row, re.S) or [None, ""])[1])
        if not m or not re.search(r"south korea|,\s*korea$", loc, re.I):
            continue
        slug, name = m.group(1), re.sub(r"^\s*20\d\d\s+", "", text(m.group(2)))
        p = fetch(f"{base}/contests/{slug}/", headers=BOT_UA, delay=1.0)
        if not p:
            continue
        fact = lambda k: text((re.search(r'<dt class="bb-eyebrow">%s</dt>\s*<dd[^>]*>(.*?)</dd>' % k, p, re.S) or [None, ""])[1])  # noqa: E731
        try:
            date = datetime.strptime(fact("Date"), "%b %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            note(f"fitnessvolt {slug}: 날짜 없음 ({fact('Date')!r})")
            continue
        parts = [x.strip() for x in (fact("Location") or loc).split(",")]
        out.append(ev("fitnessvolt", slug, "IFBB PRO", name, date, place=fact("Venue") or None,
                      city=parts[0] if len(parts) > 1 else None, url=f"{base}/contests/{slug}/"))
    return out


# ---------------------------------------------------------------- 3) unmo.kr (WNGP·MUSA·ANBC·BOB)
STOP_RUN = 30
SKIP = re.compile(r"세미나|설명회|입장권|추가\s*접수|재활")


def unmo():
    base = "https://unmo.kr"
    ids = []
    for page in range(1, 31):
        body = fetch(f"{base}/m/shop/tournament.php", params={"page": page}, delay=1.0)
        found = [int(i) for i in re.findall(r"tm_view\.php\?gs_id=(\d+)", body or "")]
        if not found:
            break
        ids += found
    if not ids:
        return []
    out, run, gid = [], 0, max(ids)
    while gid > 0 and run < STOP_RUN:
        url = f"{base}/m/shop/tm_view.php?gs_id={gid}"
        gid -= 1
        p = fetch(url, delay=1.0)
        m_t = re.search(r'og:title" content="([^"]*)"', p or "")
        m_d = re.search(r"대회 일자\s*</li>\s*<li[^>]*>(.*?)</li>", p or "", re.S)
        if not (m_t and m_d):
            run += 1  # 없는 상품
            continue
        name = html.unescape(m_t.group(1)).replace("[대회종료]", "").strip()
        start, end = parse_kdate(text(m_d.group(1)), YEAR)
        if not start or int(start[:4]) < YEAR:
            run += 1
            continue
        run = 0
        if int(start[:4]) != YEAR or SKIP.search(name):
            continue
        fed = next((f for f in ("WNGP", "MUSA", "ANBC", "BOB") if re.search(f, name, re.I)), "기타")
        short = re.sub(r"^\s*" + fed + r"\s*", "", name, flags=re.I).strip() or name
        m_p = re.search(r"대회 장소\s*</li>\s*<li[^>]*>(.*?)</li>", p, re.S)
        place = text(m_p.group(1)) if m_p else ""
        ov = next((c for k, c in OVERSEAS.items() if k in name), None)
        out.append(ev("unmo", str(gid + 1), fed, f"{fed} {short}" if fed != "기타" else short, start, end,
                      place=None if not place or "추후" in place else place, country=ov or "KR", url=url))
    log(f"  unmo: ID {max(ids)}→{gid + 1} 훑음, {YEAR}년 {len(out)}건")
    return out


# ---------------------------------------------------------------- 4) coachn 매거진 (PCA·NPCA)
def coachn():
    base = SOURCES["coachn"][1]
    posts = []
    for page in range(1, 40):
        body = fetch(base, params={"page": page}, delay=1.0)
        got = [(int(w), text(t)) for w, t in
               re.findall(r'href="[^"]*bo_table=magazine&(?:amp;)?wr_id=(\d+)[^"]*"[^>]*>(.*?)</a>', body or "", re.S)]
        got = [g for g in got if g[1]]
        if not got:
            break
        posts += got
    groups = {}
    for wid, t in sorted(set(posts), reverse=True):
        if re.match(rf"\s*\[?\s*{YEAR}\b", t) and re.search(r"N?PCA", t):
            groups.setdefault(re.sub(r"\s+", "", t)[:18], []).append((wid, t))
    out = []
    for items in groups.values():
        for wid, t in items[:3]:
            p = fetch(f"{base}&wr_id={wid}", delay=1.0)
            m = re.search(r'id="bo_v_con">(.*?)</div>', p or "", re.S)
            body = text(m.group(1)) if m else ""
            md = re.search(rf"{YEAR}\s*년\s*(\d{{1,2}})\s*월\s*(\d{{1,2}})\s*일", body)
            if not md:
                continue
            fed = re.search(r"N?PCA", t).group(0)
            mv = re.search(r"([가-힣A-Za-z0-9 ]{2,20}?)에서\s*(?:열린|개최된|진행된)\s*([가-힣A-Za-z0-9 ]+?)(?:\s*(?:보디빌딩|클래식|비키니|피지크|스포츠|머슬|여자|남자)[^ ]*\s*프로전|\s*대회|에서)", body)
            series = mv.group(2).strip() if mv else re.sub(rf"^\s*{YEAR}\s*N?PCA\s*", "", t).split()[0]
            date = f"{YEAR}-{int(md.group(1)):02d}-{int(md.group(2)):02d}"
            place = mv.group(1).strip() if mv else None
            city = (place or "").split()[0] if place else None
            out.append(ev("coachn", f"{fed}-{date}", fed, f"{fed} {series}", date, place=place, city=city,
                          url=f"{base}&wr_id={wid}"))
            break
    return out


# ---------------------------------------------------------------- 5) AFEX
def afex():
    p = fetch(SOURCES["afex"][1], headers=BOT_UA)
    if not p:
        return []
    t = text(p)
    out, seen = [], set()
    for m in re.finditer(rf"([A-Z][A-Z ]{{3,40}}?)\s+일시\s*:\s*{YEAR}\s*년\s*(\d{{1,2}})\s*월\s*(\d{{1,2}})\s*일", t):
        title = m.group(1).strip().title()
        date = f"{YEAR}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        if (title, date) in seen:
            continue
        seen.add((title, date))
        mp = re.search(r"장소\s*:\s*([^\n]+?)\s*(?:대회 안내|예매 안내|$)", t[m.end():m.end() + 300])
        out.append(ev("afex", f"{title}-{date}", "AFEX", f"AFEX {title}", date,
                      place=mp.group(1).strip() if mp else None, url=SOURCES["afex"][1]))
    return out


# ---------------------------------------------------------------- 6) fitschedule (비공식 모음)
FS_FED = [(r"NPCA", "NPCA"), (r"\bPCA", "PCA"), (r"WNGP", "WNGP"), (r"MUSA", "MUSA"), (r"ANBC", "ANBC"),
          (r"몬스터짐|monsterzym", "몬스터짐"), (r"\bAGP\b", "AGP"), (r"NPC", "NPC"), (r"NABBA", "NABBA"),
          (r"AFEX", "AFEX"), (r"ICN", "ICN"), (r"NAC", "NAC"), (r"WNC", "WNC"), (r"KBBF|대한보디빌딩|보디빌딩협회", "KBBF"),
          (r"원클래식|ONE ?CLASSIC", "ONECLASSIC"), (r"케이클래식|K-?CLASSIC", "케이클래식"), (r"머슬마니아|musclemania", "MUSCLEMANIA"),
          (r"AGONAS|아고나스", "AGONAS"), (r"WNBF", "WNBF")]


def fitschedule():
    p = fetch("https://www.fitschedule.co.kr/competitions")
    if not p:
        return []
    s = p.replace('\\"', '"')
    out = []
    for m in re.finditer(r'\{"title":"([^"]+)","date":"(\d{4}-\d\d-\d\d)"(.*?)"_locked', s):
        title, date, rest = m.groups()
        if not date.startswith(str(YEAR)):
            continue
        g = lambda k: (re.search(rf'"{k}":"([^"]*)"', rest) or [None, None])[1]  # noqa: E731
        hay = f"{title} {g('sourceName') or ''} {g('sourceId') or ''}"
        fed = next((f for pat, f in FS_FED if re.search(pat, hay, re.I)), "기타")
        out.append(ev("fitschedule", f"{fed}-{date}-{title}", fed, title, date, place=g("venue"),
                      url=g("supplementUrl") or g("officialUrl")))
    log(f"  fitschedule: {YEAR}년 {len(out)}건")
    return out


# ---------------------------------------------------------------- 7) physiquehub (비공식 모음, sitemap 확인)
def physiquehub():
    sm = fetch("https://physiquehub.kr/sitemap.xml")
    urls = [u for u in re.findall(r"<loc>([^<]+)</loc>", sm or "") if f"/competitions/{YEAR}-" in u]
    out = []
    for u in urls[:200]:
        p = fetch(u, delay=1.0)
        og = re.search(r'og:title" content="([^"]*)"', p or "")
        slug = urllib.parse.unquote(u.rsplit("/", 1)[-1])
        md = re.match(rf"{YEAR}-(.+?)-(\d\d)-(\d\d)-", slug)
        if not (og and md):
            continue
        title = html.unescape(og.group(1)).split("|")[0].strip()
        fed = next((f for pat, f in FS_FED if re.search(pat, title, re.I)), "기타")
        out.append(ev("physiquehub", slug, fed, title, f"{YEAR}-{md.group(2)}-{md.group(3)}", url=u))
    log(f"  physiquehub: sitemap {YEAR} 상세 {len(urls)}개 → {len(out)}건")
    return out


def blocked_checks():
    """쓸 수 없는 출처를 한 번씩만 확인해 기록 (우회하지 않음)."""
    for url in ("https://zerotohero.co.kr/187/?bmode=view&idx=139895280", "https://bodybuilding.or.kr/contest_kr"):
        try:
            get(url, headers=BOT_UA, tries=1)
            note(f"{url} 응답함 — 파서 미구현, 수동 확인 필요")
        except urllib.error.HTTPError as e:
            note(f"{url} → HTTP {e.code}, 건너뜀")
        except Exception as e:  # noqa: BLE001
            note(f"{url} → {str(e)[:120]}, 건너뜀")


# ---------------------------------------------------------------- 합치기
def norm(s):
    s = re.sub(r"\b20\d\d\b", "", (s or "").lower())
    return re.sub(r"[\s\-_·()\[\]#.,]+", "", s)


def similar(a, b):
    a, b = norm(a), norm(b)
    return a == b or (min(len(a), len(b)) >= 3 and (a in b or b in a)) or difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


def dedupe(events):
    out = []
    for e in events:
        dup = next((k for k in out if k["fed"] == e["fed"] and k["date"] == e["date"] and similar(k["name"], e["name"])), None)
        if dup:
            for f in ("end", "place", "city", "url"):
                if not dup.get(f) and e.get(f):
                    dup[f] = e[f]
            continue
        out.append(e)
    return out


def main():
    global YEAR
    args = sys.argv[1:]
    if "--year" in args:
        YEAR = int(args[args.index("--year") + 1])
    out_path = os.path.abspath(args[args.index("--out") + 1]) if "--out" in args else \
        os.path.join(HERE, "..", "history", f"{YEAR}.json")
    events, used = [], []
    # 순서 = 중복 시 우선순위 (공식 → 비공식)
    for key, fn in [("unmo", unmo), ("coachn", coachn), ("afex", afex), ("npcnews", npcnews),
                    ("fitnessvolt", fitnessvolt), ("fitschedule", fitschedule), ("physiquehub", physiquehub)]:
        log(f"[{key}]")
        try:
            got = fn()
        except Exception as e:  # noqa: BLE001
            note(f"{key} 실패: {str(e)[:160]}")
            got = []
        log(f"[{key}] {len(got)}건")
        if got:
            used.append(key)
            events += got
    blocked_checks()
    events = dedupe(events)
    events.sort(key=lambda e: (e["date"], e["fed"], e["name"]))
    data = {
        "year": YEAR,
        "built": datetime.now(KST).date().isoformat(),
        "sources": [{"label": SOURCES[k][0], "url": SOURCES[k][1].format(y=YEAR)} for k in used],
        "events": events,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    log(f"저장: {out_path} ({len(events)}건)")
    for n in NOTES:
        log("  note: " + n)


if __name__ == "__main__":
    main()
