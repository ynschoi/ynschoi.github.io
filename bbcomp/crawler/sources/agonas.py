"""AGONAS (내추럴 피트니스) — 접수처 잠백이 쇼핑몰(Cafe24) https://jambaekee.com/

네이버 카페는 robots.txt 금지라 쓰지 않는다. 잠백이의 AGONAS 카테고리(cate_no=75)
목록에서 상품을 찾고, 상세에서 참가비(판매가)·종목(옵션 select)·품절 여부를 읽는다.

상세의 일정·장소는 이미지에만 있어 텍스트로 읽을 수 없다. 상품명/메타 설명의
지역명(서울·수원·광명 …)으로 REF(공지된 2026 일정)를 찾아 날짜·장소를 채운다.
텍스트에 날짜가 있으면 그 값이 우선한다. 접수 마감일은 사이트에 텍스트로 없다.
"""
import re

from .common import get, log, parse_kdate, text, this_year

BASE = "https://jambaekee.com"
CATE = 75
SOURCE = {"key": "agonas", "label": "AGONAS (잠백이 접수)", "url": f"{BASE}/product/list.html?cate_no={CATE}"}
USE_REF_FALLBACK = True  # 목록에서 내려간 지역 대회도 REF 일정으로 넣을지

# 지역 → (시작일, 장소, 도시). 2026 공지 일정(카페/인스타 공지, 상세 이미지) 기준 보조값.
REF = {
    2026: {
        "수원": ("2026-07-04", "경기대학교 씨름장", "수원"),
        "광명": ("2026-07-18", "안양대학교", "광명"),
        "서울": ("2026-08-09", "밀리토피아 호텔 바이마린 (아트홀)", "성남"),
        "코리아": ("2026-08-09", "밀리토피아 호텔 바이마린 (아트홀)", "성남"),
        "KOREA": ("2026-08-09", "밀리토피아 호텔 바이마린 (아트홀)", "성남"),
    },
}


def _list_products():
    ids, page = [], 1
    while page <= 10:
        body = get(SOURCE["url"], {"page": page} if page > 1 else None)
        found = 0
        for slug, pid in re.findall(r'href="/product/([^"/]+)/(\d+)/category/%d/' % CATE, body):
            if pid not in [i for i, _ in ids]:
                ids.append((pid, slug))
                found += 1
        if not found:
            break
        page += 1
    return ids


def _options(page):
    m = re.search(r'<select[^>]*id="product_option_id1"[^>]*>(.*?)</select>', page, re.S)
    out, soldout = [], []
    for o in re.findall(r"<option[^>]*>(.*?)</option>", m.group(1) if m else "", re.S):
        o = text(o)
        if not o or "선택" in o or set(o) <= set("-— "):
            continue
        so = "[품절]" in o
        o = re.sub(r"\s*\[품절\]\s*", "", o).strip()
        if o not in out:
            out.append(o)
            soldout.append(so)
    return out, soldout


def crawl():
    year = this_year()
    prods = _list_products()
    log(f"  agonas 카테고리 {CATE}: {len(prods)}개 상품")
    events = []
    for pid, slug in prods:
        url = f"{BASE}/product/{slug}/{pid}/category/{CATE}/display/1/"
        try:
            p = get(f"{BASE}/product/detail.html", {"product_no": pid, "cate_no": CATE, "display_group": 1})
        except Exception as e:  # noqa: BLE001
            log(f"  ! agonas 상세 실패 {pid}: {e}")
            continue
        m = re.search(r"var product_name = '([^']*)'", p)
        name = text(m.group(1)) if m else text(re.sub(r"-", " ", slug))
        desc = re.search(r'<meta name="description" content="([^"]*)"', p)
        desc = text(desc.group(1)) if desc else ""
        if not re.search(r"AGONAS|아고나스", name + desc, re.I):
            continue
        my = re.search(r"(20\d\d)", name + " " + desc)
        if my and int(my.group(1)) < year:
            continue
        # 지역: 상품명 우선, 다음 메타 설명 ('AGONAS 서울 2026 접수 시작')
        region = None
        for src in (name, desc):
            r = re.search(r"(서울|수원|광명|부산|대구|인천|대전|광주|제주|성남|코리아|KOREA)", src, re.I)
            if r:
                region = r.group(1).upper() if r.group(1).isascii() else r.group(1)
                break
        if region in ("코리아", "KOREA") and re.search(r"서울", desc):
            region = "서울"
        dl = re.search(r"(?:대회\s*)?(?:일정|일시|대회일)\s*[:：]\s*([^\n]{4,60})", text(p))
        start, end = parse_kdate(dl.group(1), year) if dl else (None, None)
        ref = REF.get(year, {}).get(region or "")
        place = city = None
        if ref:
            start = start or ref[0]
            place, city = ref[1], ref[2]
        if not start:
            log(f"  - agonas 날짜 없음, 건너뜀: {name} ({pid})")
            continue
        price = re.search(r"var product_price = '(\d+)'", p)
        divisions, soldout = _options(p)
        closed = bool(re.search(r"is_soldout_icon = 'T'", p)) or (soldout and all(soldout))
        label = name if region is None or region in name else f"{name} ({region})"
        events.append({
            "id": f"agonas-{pid}", "src": "agonas", "fed": "AGONAS",
            "name": re.sub(r"^\s*20\d\d\s*", "", label).strip(),
            "date": start, "end": end, "place": place, "city": city, "country": "KR",
            "fee": f"{int(price.group(1)):,}원" if price else None, "deadline": None,
            "divisions": divisions, "host": "AGONAS", "url": url, "regUrl": url,
            "tier": "national", "major": False, "closed": bool(closed),
        })
    # 접수 상품이 내려가(404) 목록에 없는 공지 일정은 보조값으로 추가 (참가비·종목 없음)
    if USE_REF_FALLBACK:
        have = {e["date"] for e in events}
        for region, (d, place, city) in REF.get(year, {}).items():
            if d in have or region in ("코리아", "KOREA"):
                continue
            have.add(d)
            events.append({
                "id": f"agonas-ref-{d}", "src": "agonas", "fed": "AGONAS",
                "name": f"AGONAS {region}", "date": d, "end": None, "place": place, "city": city,
                "country": "KR", "fee": None, "deadline": None, "divisions": [], "host": "AGONAS",
                "url": SOURCE["url"], "regUrl": None, "tier": "national", "major": False,
            })
    return sorted(events, key=lambda e: e["date"])
