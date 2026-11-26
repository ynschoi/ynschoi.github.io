#!/usr/bin/env python3
"""출처 사이트 접속 진단: 이 서버에서 각 사이트가 열리는지 한 번씩 확인해 표로 출력한다."""
import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; bbcomp-schedule-bot/1.0; weekly personal schedule page)"
SITES = [
    ("운동의모든것", "https://unmo.kr/m/shop/tournament.php"),
    ("코치엔(PCA·NPCA)", "https://coachn.co.kr/sub/competitions_list.php"),
    ("IFBB 프로 코리아", "https://ifbbprokorea.com/schedule/"),
    ("NPC 월드와이드", "https://npcnewsonline.com/wp-json/stec/v2/get/calendars"),
    ("NABBA", "https://nabba.kr/board/com_schedule.html"),
    ("AFEX", "https://www.afex.co.kr/"),
    ("잠백이(아고나스)", "https://jambaekee.com/"),
    ("키스모스(케이클래식)", "https://kismos.co.kr/"),
    ("원클래식", "https://oneclassic.co.kr/about"),
    ("NAC", "https://www.nackorea.com/"),
    ("머슬마니아 코리아", "https://www.mmkorea.com/"),
    ("머슬마니아", "https://musclemania.com/musclemania-events-schedule/"),
    ("fitnessvolt", "https://fitnessvolt.com/bodybuilding/schedule/ifbb-pro/"),
    ("[막힘?] 대한보디빌딩협회", "https://bodybuilding.or.kr/contest_city"),
    ("[막힘?] WNC", "https://kfma.imweb.me/"),
    ("[막힘?] WNBF", "https://worldnaturalbb.com/international-events/"),
    ("[막힘?] IFBB 프로 리그", "https://www.ifbbpro.com/schedule/"),
]
for name, url in SITES:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read(200000).decode("utf-8", errors="replace")
            note = "봇 확인 화면" if "One moment, please" in body or "접근이 제한" in body else ""
            print(f"{r.status}  {len(body):>7}  {name}  {note}")
    except Exception as e:  # noqa: BLE001
        print(f"ERR  {str(e)[:60]:<60}  {name}")
    sys.stdout.flush()
