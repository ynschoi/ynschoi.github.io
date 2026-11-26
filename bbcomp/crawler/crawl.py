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
MODULES = ["unmo", "pca", "ifbbkorea", "nabba", "monsterzym", "oneclassic", "icn", "nac", "agonas", "ifbbpro_world"]
ACCUMULATE = {"pca"}
FIELDS = ["place", "city", "country", "fee", "deadline", "divisions", "qualification", "proCards",
          "host", "url", "regUrl", "end"]


def norm(s):
    return re.sub(r"[\s\-_·()\[\]#]+", "", (s or "").lower())


def dedupe(events):
    out, seen = [], {}
    for e in events:
        key = (e.get("fed"), e["date"], norm(e.get("name"))[:12])
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
    e.setdefault("country", "KR")
    e.setdefault("tier", "national" if e["country"] == "KR" else "international")
    if e.get("divisions"):
        e["divisions"] = [d.strip() for d in e["divisions"] if d and d.strip()]
    return e


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
        except ModuleNotFoundError:
            log(f"[{key}] 모듈 없음 — 건너뜀")
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

    events = dedupe(sorted(events, key=lambda e: MODULES.index(e["src"]) if e["src"] in MODULES else 99))
    events.sort(key=lambda e: (e["date"], e.get("fed", ""), e.get("name", "")))
    data = {"generated": now, "sources": sources, "events": events}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    log(f"저장: {out} ({len(events)}건)")
    if not any(s.get("ok") for s in sources.values()):
        sys.exit(1)  # 전부 실패 → 워크플로 실패 표시(메일 알림)


if __name__ == "__main__":
    main()
