#!/usr/bin/env python3
"""data.json → 구독용 캘린더(.ics) 파일들.

아이폰·삼성·구글 캘린더에서 URL로 '구독'하면 매주 수집 때마다 바뀐 일정이 자동 반영된다.
  bbcomp/cal/kr.ics           국내 전체
  bbcomp/cal/kr-pro.ics       국내 프로카드·프로쇼
  bbcomp/cal/world-pro.ics    해외 프로 퀄리파이어·프로쇼
  bbcomp/cal/fed-<slug>.ics   연맹별 (국내)
"""
import json
import os
import re
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "cal")
SITE = "https://ynschoi.github.io/bbcomp/"

FED_SLUG = {"PCA": "pca", "NPCA": "npca", "WNGP": "wngp", "MUSA": "musa", "ANBC": "anbc", "BOB": "bob",
            "NPC": "npc", "AGP": "agp", "IFBB PRO": "ifbbpro", "NABBA": "nabba", "AFEX": "afex",
            "AGONAS": "agonas", "케이클래식": "kclassic", "ONECLASSIC": "oneclassic", "NAC": "nac", "ICN": "icn",
            "WNBF": "wnbf", "MUSCLEMANIA": "musclemania", "KBBF": "kbbf", "WNC": "wnc", "몬스터짐": "monsterzym"}


def esc(s):
    return re.sub(r"([\\,;])", r"\\\1", str(s)).replace("\n", "\\n")


def fold(line):
    """RFC 5545: 75바이트마다 줄 접기."""
    b = line.encode("utf-8")
    if len(b) <= 75:
        return line
    out, cur = [], b""
    for ch in line:
        c = ch.encode("utf-8")
        if len(cur) + len(c) > 74:
            out.append(cur.decode("utf-8"))
            cur = b" "
        cur += c
    out.append(cur.decode("utf-8"))
    return "\r\n".join(out)


def level(e):
    n = e.get("name", "")
    if e.get("fed") == "IFBB PRO":
        return "pro"
    if re.search(r"퀄리파이어|qualifier|아마추어 올림피아|amateur olympia", n, re.I) or e.get("proCards"):
        return "pq"
    return None


def title(e):
    n, f = e.get("name", ""), e.get("fed", "")
    return n if f == "기타" or n.upper().startswith(f.upper()) else f"{f} {n}"


def vevent(e, stamp):
    d0 = date.fromisoformat(e["date"])
    d1 = date.fromisoformat(e.get("end") or e["date"]) + timedelta(days=1)
    desc = [x for x in (
        e.get("fee") and f"참가비 {e['fee']}",
        e.get("deadline") and f"접수 마감 {e['deadline']}",
        e.get("divisions") and "종목 " + ", ".join(e["divisions"][:20]) + (" 외" if len(e["divisions"]) > 20 else ""),
        e.get("url") and f"원문 {e['url']}",
        f"전체 일정 {SITE}",
        "※ 일정은 주최 측 사정으로 바뀔 수 있어요",
    ) if x]
    loc = ", ".join(x for x in (e.get("place"), e.get("city")) if x)
    lines = ["BEGIN:VEVENT", f"UID:{e['id']}@bbcomp", f"DTSTAMP:{stamp}",
             f"DTSTART;VALUE=DATE:{d0:%Y%m%d}", f"DTEND;VALUE=DATE:{d1:%Y%m%d}",
             f"SUMMARY:{esc(title(e))}", f"DESCRIPTION:{esc(chr(10).join(desc))}"]
    if loc:
        lines.append(f"LOCATION:{esc(loc)}")
    if e.get("url"):
        lines.append(f"URL:{e['url']}")
    if e.get("closed") and e["date"] >= stamp[:4]:
        pass
    lines.append("END:VEVENT")
    return lines


def write(name, label, events, stamp):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//BoCal//schedule//KO", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", f"X-WR-CALNAME:{esc(label)}", "X-WR-TIMEZONE:Asia/Seoul",
             "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D"]
    for e in events:
        lines += vevent(e, stamp)
    lines.append("END:VCALENDAR")
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(fold(l) for l in lines) + "\r\n")


def main():
    with open(os.path.join(ROOT, "data.json"), encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(OUT, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    since = (date.today() - timedelta(days=60)).isoformat()  # 지난 대회는 두 달만 남긴다
    ev = [e for e in data["events"] if e.get("date", "") >= since]
    kr = [e for e in ev if e.get("country", "KR") == "KR"]
    ww = [e for e in ev if e.get("country", "KR") != "KR"]
    feeds = [("kr.ics", "BoCal · 국내 전체", kr),
             ("kr-pro.ics", "BoCal · 국내 프로카드·프로쇼", [e for e in kr if level(e)]),
             ("world-pro.ics", "BoCal · 해외 프로", [e for e in ww if level(e)])]
    for fed, slug in FED_SLUG.items():
        es = [e for e in kr if e.get("fed") == fed]
        if es:
            feeds.append((f"fed-{slug}.ics", f"BoCal · {fed}", es))
    for name, label, es in feeds:
        write(name, label, es, stamp)
    index = [{"file": n, "label": l, "count": len(es)} for n, l, es in feeds]
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"캘린더 {len(feeds)}개 생성: " + ", ".join(f"{n}({len(es)})" for n, _, es in feeds))


if __name__ == "__main__":
    main()
