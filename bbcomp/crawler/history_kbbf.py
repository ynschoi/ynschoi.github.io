#!/usr/bin/env python3
"""history/<작년>.json 에 대한보디빌딩협회 대회가 없으면 협회 게시판의 작년 카테고리에서 채운다 (한 번만).
협회 사이트는 일부 클라우드에서 막혀 GitHub Actions에서 돌린다."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sources import kbbf  # noqa: E402
from sources.common import this_year  # noqa: E402

year = this_year() - 1
path = os.path.join(HERE, "..", "history", f"{year}.json")
data = {"year": year, "sources": [], "events": []}
if os.path.exists(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
if any(e.get("fed") == "KBBF" for e in data["events"]):
    print("이미 있음 — 건너뜀")
    sys.exit(0)
got = kbbf.crawl(years=[year])
for e in got:
    data["events"].append({"id": f"h{year}-kbbf-{e['id']}", "fed": "KBBF", "name": e["name"], "date": e["date"],
                           "end": e.get("end"), "place": e.get("place"), "city": None, "country": "KR",
                           "src": "대한보디빌딩협회", "url": e.get("url")})
data["sources"].append({"label": "대한보디빌딩협회", "url": kbbf.SOURCE["url"]})
data["events"].sort(key=lambda e: (e["date"], e["fed"], e["name"]))
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print(f"KBBF {year} {len(got)}건 추가")
