"""케이클래식 (K-CLASSIC) — 접수처 KISMOS 쇼핑몰(Cafe24) 카테고리 822 '2026 KCL'
https://kismos.co.kr/product/list.html?cate_no=822

목록의 상품(대회별 일반/내추럴)을 모두 찾고, 상세에서 종목(첫 옵션 select)·품절 여부를 읽는다.
대회 일시·장소·접수기간·참가비 단계는 상세 이미지에만 있어 텍스트로 읽을 수 없으므로
REF(상세 이미지에 적힌 2026 일정)를 도시명으로 찾아 채운다. 새 도시가 생기면 REF에 추가.
"""
import re

from .common import get, log, parse_kdate, text, this_year

BASE = "https://kismos.co.kr"
CATE = 822
SOURCE = {"key": "kclassic", "label": "케이클래식 (K-CLASSIC)", "url": f"{BASE}/product/list.html?cate_no={CATE}"}

# 도시 → (대회일, 장소, 접수 마감(추가 신청 종료), 참가비 표기) — 2026 상세 이미지 기준
REF = {
    2026: {
        "대구": ("2026-04-11", "대구 엑스코", "2026-03-29",
                 "얼리버드 14만원 / 일반 17만원 / 추가 20만원 (종목 추가 8만원)"),
        "서울": ("2026-05-30", "에스플렉스센터", "2026-05-17",
                 "얼리버드 14만원 / 일반 17만원 / 추가 20만원 (종목 추가 8만원)"),
        "부산": ("2026-10-31", "피아크 별관 아트홀", "2026-10-25",
                 "얼리버드 14만원 / 일반 17만원 / 추가 20만원 (종목 추가 8만원)"),
    },
}
CITIES = r"(서울|부산|대구|인천|광주|대전|울산|제주|수원|창원|청주|전주|강릉)"


def _list_products():
    ids, page = [], 1
    while page <= 10:
        body = get(SOURCE["url"], {"page": page} if page > 1 else None)
        found = 0
        for pid in re.findall(r'product_no=(\d+)&(?:amp;)?cate_no=%d' % CATE, body):
            if pid not in ids:
                ids.append(pid)
                found += 1
        if not found:
            break
        page += 1
    return ids


def _divisions(page):
    m = re.search(r'<select[^>]*id="product_option_id1"[^>]*>(.*?)</select>', page, re.S)
    out, soldout = [], []
    for o in re.findall(r"<option[^>]*>(.*?)</option>", m.group(1) if m else "", re.S):
        o = text(o)
        if not o or "선택" in o or "추가 신청" in o or set(o) <= set("-— "):
            continue
        so = "[품절]" in o
        o = re.sub(r"\s*\(\+[\d,]+원\)|\s*\[품절\]", "", o).strip()
        if o not in out:
            out.append(o)
            soldout.append(so)
    return out, soldout


def crawl():
    year = this_year()
    ids = _list_products()
    log(f"  kclassic 카테고리 {CATE}: {len(ids)}개 상품")
    events = []
    for pid in ids:
        url = f"{BASE}/product/detail.html?product_no={pid}&cate_no={CATE}&display_group=1"
        try:
            p = get(url)
        except Exception as e:  # noqa: BLE001
            log(f"  ! kclassic 상세 실패 {pid}: {e}")
            continue
        m = re.search(r"var product_name = '([^']*)'", p)
        name = text(m.group(1)) if m else ""
        if not re.search(r"케이\s*클래식|K-?CLASSIC|KCL", name, re.I):
            continue
        my = re.search(r"(20\d\d)", name)
        if my and int(my.group(1)) < year:
            continue
        c = re.search(CITIES, name)
        city = c.group(1) if c else None
        dl = re.search(r"대회\s*(?:일시|일자)\s*[:：]?\s*([^\n]{4,40})", text(p))
        start, end = parse_kdate(dl.group(1), year) if dl else (None, None)
        ref = REF.get(year, {}).get(city or "")
        place = deadline = fee = None
        if ref:
            start = start or ref[0]
            place, deadline, fee = ref[1], ref[2], ref[3]
        if not start:
            log(f"  - kclassic 날짜 없음, 건너뜀: {name} ({pid})")
            continue
        if not fee:
            pm = re.search(r"\(\+([\d,]+)원\)", p)
            fee = f"{pm.group(1)}원" if pm else None
        divisions, soldout = _divisions(p)
        natural = "내추럴" in name
        events.append({
            "id": f"kclassic-{pid}", "src": "kclassic", "fed": "케이클래식",
            "name": re.sub(r"^\s*20\d\d\s*", "", name).strip(),
            "date": start, "end": end, "place": place, "city": city, "country": "KR",
            "fee": fee, "deadline": deadline, "divisions": divisions,
            "qualification": "내추럴(약물 검사)" if natural else None,
            "host": "케이클래식 (KISMOS)", "url": url, "regUrl": url,
            "tier": "national", "major": False,
            "closed": bool(re.search(r"is_soldout_icon = 'T'", p)) or bool(soldout and all(soldout)),
        })
    return sorted(events, key=lambda e: (e["date"], e["name"]))
