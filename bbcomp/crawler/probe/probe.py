#!/usr/bin/env python3
"""구조 진단용: 이 환경에서 열리지 않는 사이트의 페이지 구조를 GitHub 러너 로그로 확인한다 (일회성)."""
import html
import re
import urllib.request

UA = "Mozilla/5.0 (compatible; bbcomp-schedule-bot/1.0; weekly personal schedule page)"
URLS = [
    "https://bodybuilding.or.kr/robots.txt",
    "https://bodybuilding.or.kr/contest_city",
    "https://bodybuilding.or.kr/contest_kr",
    "https://kfma.imweb.me/robots.txt",
    "https://kfma.imweb.me/",
]


def fetch(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


for u in URLS:
    print("=" * 30, u)
    try:
        t = fetch(u)
    except Exception as e:  # noqa: BLE001
        print("ERR", e)
        continue
    if u.endswith("robots.txt"):
        print(t[:1500])
        continue
    links = sorted(set(re.findall(r'href="([^"]*(?:bmode=view|idx=|contest|board|schedule|notice)[^"]*)"', t)))
    print("LINKS", len(links))
    for l in links[:60]:
        print("  ", html.unescape(l))
    classes = sorted(set(re.findall(r'class="([^"]*(?:list|board|title|subject|date|item|post)[^"]*)"', t)))[:60]
    print("CLASSES", classes)
    i = t.find("bmode=view")
    if i > 0:
        print("SNIPPET", re.sub(r"\s+", " ", t[max(0, i - 1500):i + 2500]))
    body = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", t)
    txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))
    print("TEXT", txt[:3000])
    # 첫 상세 글 한 개
    m = re.search(r'href="([^"]*bmode=view[^"]*)"', t)
    if m:
        du = html.unescape(m.group(1))
        du = du if du.startswith("http") else re.match(r"https://[^/]+", u).group(0) + du
        print("-" * 20, "DETAIL", du)
        try:
            d = fetch(du)
            body = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", d)
            print("DTEXT", re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))[:4000])
            print("DCLASSES", sorted(set(re.findall(r'class="([^"]*(?:board|title|subject|date|content|post|view)[^"]*)"', d)))[:50])
            print("DFILES", sorted(set(re.findall(r'href="([^"]*(?:download|\.pdf|\.hwp|file)[^"]*)"', d)))[:10])
        except Exception as e:  # noqa: BLE001
            print("DERR", e)
