"""크롤러 공통 함수 (표준 라이브러리만 사용)."""
import html
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
DELAY = 0.4  # 요청 간 간격(초)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


_ROBOTS = {}


class RobotsDisallowed(Exception):
    pass


def allowed(url):
    """robots.txt가 이 URL을 막으면 False. robots.txt가 없거나(404) 읽을 수 없으면 허용으로 본다."""
    import urllib.robotparser
    p = urllib.parse.urlsplit(url)
    root = f"{p.scheme}://{p.netloc}"
    rp = _ROBOTS.get(root)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(root + "/robots.txt", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                rp.parse(r.read().decode("utf-8", errors="replace").splitlines())
        except Exception:  # noqa: BLE001
            rp.parse([])
        _ROBOTS[root] = rp
    return rp.can_fetch("*", url)


def get(url, params=None, data=None, headers=None, tries=3, delay=DELAY):
    """GET(또는 data가 있으면 POST) → str. robots.txt 금지 경로면 RobotsDisallowed.
    429/5xx·네트워크 오류는 지수 백오프 재시도."""
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    if not allowed(url):
        raise RobotsDisallowed(f"robots.txt 금지: {url}")
    body = urllib.parse.urlencode(data).encode() if isinstance(data, dict) else data
    h = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"}
    h.update(headers or {})
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=body, headers=h)
            with urllib.request.urlopen(req, timeout=40) as r:
                raw = r.read()
                cs = r.headers.get_content_charset() or "utf-8"
            time.sleep(delay)
            return raw.decode(cs, errors="replace")
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except Exception as e:  # noqa: BLE001
            last = e
        wait = 5 * (2 ** i)
        log(f"  ! {url} ({last}) — {wait}s 후 재시도")
        time.sleep(wait)
    raise RuntimeError(f"요청 실패: {url} ({last})")


def text(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s or "")
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


def iso(y, m, d):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def this_year():
    return datetime.now(KST).year


def parse_kdate(s, year_hint=None):
    """'2026년 12월 5일', '2026-12-12', '2026.8.15~16', '8월 15일 ~ 8월 16일' → (start, end|None)"""
    year_hint = year_hint or this_year()
    s = s or ""
    m = re.search(r"(\d{4})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        start = iso(y, mo, d)
        m2 = re.search(r"^\s*\.?\s*(?:\([^)]*\)|[월화수목금토일]요일)?\s*[~\-–]\s*(?:(\d{4})\s*[-./]\s*)?(?:(\d{1,2})\s*[-./]\s*)?(\d{1,2})\b",
                       s[m.end():])
        end = iso(m2.group(1) or y, m2.group(2) or mo, m2.group(3)) if m2 else None
        return start, (end if end and end > start else None)
    m = re.search(r"(?:(\d{4})\s*년\s*)?(\d{1,2})\s*월\s*(\d{1,2})\s*일", s)
    if not m:
        return None, None
    y = int(m.group(1) or year_hint)
    start = iso(y, m.group(2), m.group(3))
    m2 = re.search(r"^\s*(?:\([^)]*\)|[월화수목금토일]요일)?\s*[~\-–]\s*(?:(\d{1,2})\s*월\s*)?(\d{1,2})\s*일", s[m.end():])
    end = iso(y, m2.group(1) or m.group(2), m2.group(2)) if m2 else None
    return start, (end if end and end > start else None)
