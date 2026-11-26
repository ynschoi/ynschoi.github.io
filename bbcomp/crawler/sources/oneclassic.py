"""ONE CLASSIC 피트니스 챔피언쉽 (oneclassic.co.kr) — 현재 회차 1건만 노출하는 Next.js 사이트.

/about(대회일정) 서버 렌더링 텍스트에서 날짜·장소·접수일정·종목을, /register/notice에서 참가비를,
/register에서 구글폼 접수 링크를 읽는다.
"""
import re
import urllib.robotparser

from .common import UA, get, iso, log, text

SOURCE = {"key": "oneclassic", "label": "ONE CLASSIC", "url": "https://oneclassic.co.kr/"}
BASE = "https://oneclassic.co.kr"


def _robots_ok(url):
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.parse(get(BASE + "/robots.txt").splitlines())
    except Exception as e:  # noqa: BLE001  robots.txt 없음/오류 → 제한 없음으로 간주
        log(f"  [oneclassic] robots.txt 읽기 실패({e}) — 허용으로 간주")
        return True
    return rp.can_fetch(UA, url)


def _lines(html):
    """태그 경계마다 줄을 나눈 텍스트 줄 목록."""
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html or "")
    return [l.strip() for l in text(re.sub(r"<[^>]+>", "\n", html)).split("\n") if l.strip()]


def _after(lines, label, n=1):
    """label 줄 다음 n번째 줄."""
    for i, l in enumerate(lines):
        if l == label and i + n < len(lines):
            return lines[i + n]
    return None


DOT_DATE = r"(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})"


def _dot(s):
    m = re.search(DOT_DATE, s or "")
    return iso(*m.groups()) if m else None


def _fee(lines):
    """'1차 얼리버드 / 2월 1일 – 2월 28일 / ₩ / 190,000 / +₩ / 90,000' 형태의 표."""
    parts = []
    for label in ("1차 얼리버드", "2차 얼리버드", "정상가"):
        for i, l in enumerate(lines):
            if l == label:
                nums = []
                for x in lines[i + 1:i + 9]:
                    if re.fullmatch(r"[\d,]{5,}", x):
                        nums.append(x)
                if nums:
                    s = f"{label} {nums[0]}원"
                    if len(nums) > 1:
                        s += f"(중복 +{nums[1]}원)"
                    parts.append(s)
                break
    return " / ".join(parts) or None


def crawl():
    url = BASE + "/about"
    if not _robots_ok(url):
        log("  [oneclassic] robots.txt가 /about 접근을 허용하지 않음 — 건너뜀")
        return []
    L = _lines(get(url))

    # 날짜: 'Date' 다음 줄 '2026. 05. 16 — 17'
    dline = _after(L, "Date") or next((l for l in L if re.search(DOT_DATE, l)), "")
    m = re.search(DOT_DATE + r"(?:\s*[—–~\-]\s*(?:(\d{1,2})\s*\.\s*)?(\d{1,2}))?", dline)
    if not m:
        log("  [oneclassic] 대회 날짜를 찾지 못함")
        return []
    y, mo, d, mo2, d2 = m.groups()
    date = iso(y, mo, d)
    end = iso(y, mo2 or mo, d2) if d2 else None
    if end and end <= date:
        end = None

    place = _after(L, "Venue")
    city = _after(L, "Venue", 2)
    if city and (city.startswith("Prize") or "₩" in city):
        city = None
    deadline = _dot(_after(L, "접수 마감", 2) or "")
    edition = next((l for l in L if re.fullmatch(r"제\s*\d+\s*회 대회", l)), None)

    # 종목: 'Bodybuilding / 규정 확인 / 보디빌딩' 패턴(종목 안내 블록)
    divisions = []
    for i, l in enumerate(L):
        if l == "규정 확인" and i + 1 < len(L) and re.search(r"[가-힣]", L[i + 1]):
            if L[i + 1] not in divisions:
                divisions.append(L[i + 1])
    if not divisions:  # 홈 카드 'Bodybuilding / 보디빌딩 / 01'
        for i, l in enumerate(L[:-2]):
            if re.fullmatch(r"0\d", L[i + 2]) and re.search(r"[가-힣]", L[i + 1]) and L[i + 1] not in divisions:
                divisions.append(L[i + 1])

    fee = reg = None
    try:
        fee = _fee(_lines(get(BASE + "/register/notice")))
    except Exception as e:  # noqa: BLE001
        log(f"  [oneclassic] 참가비 페이지 실패: {e}")
    try:
        m = re.search(r"https://(?:forms\.gle|docs\.google\.com/forms)/[^\"'\\\s<>]+", get(BASE + "/register"))
        reg = m.group(0) if m else BASE + "/register"
    except Exception as e:  # noqa: BLE001
        log(f"  [oneclassic] 접수 페이지 실패: {e}")
        reg = BASE + "/register"

    name = "ONE CLASSIC 피트니스 챔피언쉽"
    if edition:
        name = f"{edition.replace(' 대회', '')} {name}"
    return [{
        "id": f"oneclassic-{y}",
        "fed": "ONECLASSIC",
        "name": name,
        "date": date,
        "end": end,
        "place": place,
        "city": city,
        "country": "KR",
        "fee": fee,
        "deadline": deadline,
        "divisions": divisions,
        "qualification": "종목별 네추럴(1일차)·오픈(2일차) 부문" if any(l.startswith("Day 1") for l in L) else None,
        "host": "ONE CLASSIC",
        "url": url,
        "regUrl": reg,
        "tier": "national",
        "major": True,
    }]
