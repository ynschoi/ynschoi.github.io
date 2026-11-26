#!/usr/bin/env python3
"""보디빌딩 대회일정 크롤러 실행기 → bbcomp/data.json

출처별 모듈은 sources/<key>.py (SOURCE, crawl()). 스키마는 sources/__init__.py 참고.

규칙
  - 출처 하나가 실패하거나 0건이면 그 출처의 기존 데이터를 유지 (앱이 비지 않도록)
  - ACCUMULATE 출처는 이번에 안 보인 과거 대회도 보관 (현재 회차만 노출하는 사이트용)
  - 같은 연맹·같은 날·비슷한 이름은 하나로 합침 (먼저 나온 출처 우선, 빈 필드는 서로 보충)
사용
  python3 bbcomp/crawler/crawl.py                 # 전체
  python3 bbcomp/crawler/crawl.py unmo pca        # 일부 출처만 다시 수집
  python3 bbcomp/crawler/crawl.py --out x.json
"""
import importlib
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sources.common import KST, log  # noqa: E402

DEFAULT_OUT = os.path.join(HERE, "..", "data.json")
# 순서 = 중복 시 우선순위
MODULES = ["unmo", "pca", "ifbbkorea", "kbbf", "nabba", "afex", "agonas", "kclassic", "oneclassic", "nac",
           "musclemania", "wnbf", "fitnessvolt", "ifbbpro_world"]
# 제외: monsterzym(robots.txt 전체 금지 → NPC 월드와이드 캘린더로 대체), kbbf·wnc(접근 제한 403),
#       icn(사이트 내부 DB API 직접 호출 필요 — 사용하지 않음)
ACCUMULATE = {"pca", "fitnessvolt"}
FIELDS = ["place", "city", "country", "fee", "deadline", "divisions", "qualification", "proCards",
          "host", "url", "regUrl", "end"]


def norm(s):
    return re.sub(r"[\s\-_·()\[\]#]+", "", (s or "").lower())


def pro_key(name):
    n = re.sub(r"^\s*20\d\d\s+", "", (name or "").lower())
    return re.sub(r"[^a-z0-9]+", "", n)


def korea_pro_cleanup(events):
    """국내 프로 대회 정리.
    - IFBB 프로 리그 전체 일정(ifbbpro_world)의 한국 AGP·아마추어 올림피아는 IFBB 프로 코리아(공식, 한글·종목·참가비 있음)와 겹치므로 뺀다
    - 몬스터짐 프로쇼·퀄리파이어의 영문 이름은 같은 날 몬스터짐 리저널의 한글 대회명으로 바꾼다"""
    have_kor = any(e["src"] == "ifbbkorea" for e in events)
    out = []
    for e in events:
        n = e.get("name", "")
        if have_kor and e["src"] in ("ifbbpro_world", "fitnessvolt") and e.get("country") == "KR" \
                and re.search(r"\bAGP\b|Amateur Olympia", n, re.I):
            continue
        out.append(e)
    mz_title = {}
    for e in out:
        if e.get("fed") == "몬스터짐" and re.search(r"[가-힣]", e.get("name", "")):
            mz_title.setdefault(e["date"], e["name"].split(" (")[0])
    for e in out:
        n = e.get("name", "")
        if e.get("fed") == "몬스터짐" and not re.search(r"[가-힣]", n):
            base = mz_title.get(e["date"], "몬스터짐")
            kind = "프로 퀄리파이어" if re.search(r"qualifier", n, re.I) else "IFBB 프로쇼"
            if re.search(r"natural", n, re.I):
                kind = "내추럴 " + kind
            e["name"] = f"{base} ({kind})"
            e["major"] = True
            if any(x is not e and x.get("fed") == "몬스터짐" and x["date"] == e["date"] and kind in x.get("name", "")
                   for x in out):
                e["_drop"] = True  # 같은 날 같은 종류(예: '오픈 프로 퀄리파이어')가 이미 있음
    return [e for e in out if not e.pop("_drop", False)]


def dedupe(events):
    """같은 출처 안에서는 이름 전체가 같을 때만, 다른 출처끼리는 같은 연맹·날짜·전체 이름일 때 합친다."""
    out, seen = [], {}
    for e in events:
        key = (e.get("fed"), e["date"], norm(e.get("name")))
        if key in seen:
            keep = seen[key]
            for f in FIELDS:
                if not keep.get(f) and e.get(f):
                    keep[f] = e[f]
            continue
        seen[key] = e
        out.append(e)
    return out


def clean(e, key):
    e = {k: v for k, v in e.items() if v not in (None, "", [])}
    e["src"] = key
    # 해외 일정 출처는 국가가 비어 있으면 '?'(한국으로 오인하지 않게), 국내 출처만 기본 KR
    e.setdefault("country", "?" if key in ("ifbbpro_world", "fitnessvolt", "musclemania", "wnbf") else "KR")
    e.setdefault("tier", "national" if e["country"] == "KR" else "international")
    if e.get("divisions"):
        e["divisions"] = [d.strip() for d in e["divisions"] if d and d.strip()]
    if key == "ifbbpro_world" and e.get("country") in ("KR", "MN") and re.search(r"monsterzym|asian champ", e.get("name", ""), re.I):
        localize_monsterzym(e)
    return e


# 몬스터짐 대회는 NPC 월드와이드 공식 캘린더(npcnewsonline)에서 가져온다 (event.monsterzym.com은 robots.txt 전체 금지)
MZ_NAMES = [("show man", "쇼맨"), ("kim jun ho", "김준호 클래식"), ("black chrome", "블랙크롬"), ("overwhelm", "압도"),
            ("asian champ", "아시안 챔피언십"), ("mongolia", "몽골 챔피언십"), ("natural pro qualifier", "코리아 내추럴 파이널"),
            ("natural regional", "코리아 내추럴 파이널")]
MZ_KIND = [("natural pro qualifier", "내추럴 프로 퀄리파이어"), ("open pro qualifier", "오픈 프로 퀄리파이어"),
           ("pro qualifier", "프로 퀄리파이어"), ("natural regional", "내추럴 리저널"), ("open regional", "오픈 리저널")]


def localize_monsterzym(e):
    n = e["name"].lower()
    title = next((k for en, k in MZ_NAMES if en in n), None)
    kind = next((k for en, k in MZ_KIND if en in n), "")
    e["fed"] = "몬스터짐"
    e["tier"] = "international" if e.get("country") == "MN" else "national"
    if title:
        e["name"] = f"{title} ({kind})" if kind else title
    e["host"] = e.get("host") or "MONSTERZYM"
    e["major"] = e.get("major") or "qualifier" in n or "champ" in n


TRACK = {"date": "날짜", "end": "종료일", "place": "장소", "fee": "참가비", "deadline": "접수 마감"}


def track_changes(events, old, now):
    """이전 data.json과 비교해 바뀐 일정을 기록한다.
    - 각 대회: firstSeen(처음 수집된 날), changes(최근 변경 5개)
    - 전체: changelog(최근 90일 변경·신규 목록)"""
    prev = {e["id"]: e for e in old.get("events", [])}
    first_run = not prev
    log_ = [c for c in old.get("changelog", []) if c.get("at", "") >= _days_ago(now, 90)]
    for e in events:
        p = prev.get(e["id"])
        if p is None:
            e["firstSeen"] = now[:10]
            if not first_run and e.get("date", "") >= now[:10]:
                log_.append({"at": now[:10], "id": e["id"], "kind": "new", "name": e.get("name"), "fed": e.get("fed")})
            continue
        e["firstSeen"] = p.get("firstSeen", now[:10])
        ch = list(p.get("changes", []))
        for f, label in TRACK.items():
            a, b = p.get(f), e.get(f)
            if a and b and a != b:
                c = {"at": now[:10], "field": f, "label": label, "from": a, "to": b}
                ch.append(c)
                log_.append({**c, "id": e["id"], "kind": "change", "name": e.get("name"), "fed": e.get("fed")})
        if ch:
            e["changes"] = ch[-5:]
    log_.sort(key=lambda c: c["at"], reverse=True)
    return log_[:300]


def _days_ago(now, n):
    from datetime import date, timedelta
    return (date.fromisoformat(now[:10]) - timedelta(days=n)).isoformat()


def main():
    args = sys.argv[1:]
    out = os.path.abspath(args[args.index("--out") + 1]) if "--out" in args else os.path.abspath(DEFAULT_OUT)
    only = [a for a in args if a in MODULES]

    old = {"events": [], "sources": {}}
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            old = json.load(f)
    prev_by = {}
    for e in old.get("events", []):
        prev_by.setdefault(e.get("src"), []).append(e)

    now = datetime.now(KST).isoformat(timespec="minutes")
    events, sources = [], dict(old.get("sources", {}))
    for key in MODULES:
        prev = prev_by.get(key, [])
        try:
            mod = importlib.import_module(f"sources.{key}")
        except Exception as e:  # noqa: BLE001  모듈 없음·작성 중 오류 → 기존 데이터 유지
            log(f"[{key}] 모듈 불러오기 실패 — 건너뜀 ({e})")
            events += prev
            continue
        if only and key not in only:
            events += prev
            continue
        log(f"[{key}] 수집 시작")
        t0 = time.time()
        try:
            got = [clean(e, key) for e in mod.crawl() if e.get("date")]
            err = None
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            got, err = [], str(e)[:200]
        if got and key in ACCUMULATE:
            ids = {e["id"] for e in got}
            got += [e for e in prev if e["id"] not in ids]
        info = {"label": mod.SOURCE["label"], "url": mod.SOURCE["url"], "checked": now}
        if got:
            events += got
            sources[key] = {**info, "ok": True, "count": len(got), "updated": now}
        else:
            events += prev
            sources[key] = {**sources.get(key, {}), **info, "ok": False, "count": len(prev),
                            "error": err or "0건"}
        log(f"[{key}] {'성공' if got else '실패 — 기존 데이터 유지'}: {sources[key]['count']}건 ({time.time()-t0:.0f}s)")

    # IFBB 프로쇼: 공식(ifbbpro.com)이 받아지면 그걸 쓰고, fitnessvolt는 종목 보충과 공식이 실패했을 때 대체용
    official = [e for e in events if e["src"] == "ifbbpro_world" and e.get("fed") == "IFBB PRO"]
    if official:
        fv = {(e["date"], pro_key(e["name"])): e for e in events if e["src"] == "fitnessvolt"}
        for e in official:
            m = fv.get((e["date"], pro_key(e["name"])))
            if m and not e.get("divisions") and m.get("divisions"):
                e["divisions"] = m["divisions"]
        events = [e for e in events if e["src"] != "fitnessvolt"]
    # 국내 AGP 프로쇼는 IFBB 프로 코리아(공식)에 있으므로 비공식 출처의 같은 대회는 뺀다
    if any(e["src"] == "ifbbkorea" for e in events):
        events = [e for e in events if not (e["src"] == "fitnessvolt" and e.get("country") == "KR" and "AGP" in e.get("name", ""))]
    events = korea_pro_cleanup(events)
    events = dedupe(sorted(events, key=lambda e: MODULES.index(e["src"]) if e["src"] in MODULES else 99))
    events.sort(key=lambda e: (e["date"], e.get("fed", ""), e.get("name", "")))
    changelog = track_changes(events, old, now)
    data = {"generated": now, "sources": sources, "events": events, "changelog": changelog}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    log(f"저장: {out} ({len(events)}건)")
    if not any(s.get("ok") for s in sources.values()):
        sys.exit(1)  # 전부 실패 → 워크플로 실패 표시(메일 알림)


if __name__ == "__main__":
    main()
