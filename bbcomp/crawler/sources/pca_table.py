"""PCA KOREA · NPCA 상반기 보충 — 공식 출처(코치엔)에 날짜가 안 남은 대회만.

코치엔은 접수 중·최근 대회와 결과 기사만 보여줘서, 기사가 없는 상반기 PCA/NPCA 대회는 날짜를 알 수 없다.
그 빈칸을 인스타 ms_leaders '2026년 대회일정' 표(사용자 제공 이미지)로 채운다.
- 같은 연맹·같은 날 공식(pca) 대회가 있으면 crawl.py에서 이 보충분은 빠진다.
- 비공식이므로 unofficial 표시 → 앱 상세에 '주최 측 공지 확인 필요' 안내.
표에 새 대회가 생기거나 공식 출처가 생기면 아래 TABLE을 고치거나 지운다.
"""
SOURCE = {"key": "pca_table", "label": "PCA·NPCA 상반기 보충 (ms_leaders 일정표)",
          "url": "https://www.instagram.com/ms_leaders/"}
NOTE = "ms_leaders 2026 대회일정 표 (비공식 · 주최 측 공지 확인 필요)"

# (날짜, 연맹, 이름) — 이름은 공식 pca 모듈과 같은 'CITY POINT LEAGUE' 꼴(앱이 도시명으로 줄여 보여줌)
TABLE = [
    ("2026-04-04", "PCA", "SEOUL POINT LEAGUE"), ("2026-04-05", "NPCA", "SEOUL POINT LEAGUE"),
    ("2026-04-11", "PCA", "아시안 챔피언십"), ("2026-04-12", "NPCA", "아시안 챔피언십"),
    ("2026-04-18", "PCA", "GWANGJU POINT LEAGUE"), ("2026-04-19", "NPCA", "GWANGJU POINT LEAGUE"),
    ("2026-04-25", "PCA", "JEONBUK POINT LEAGUE"), ("2026-04-26", "NPCA", "JEONBUK POINT LEAGUE"),
    ("2026-05-02", "PCA", "SEONGNAM POINT LEAGUE"), ("2026-05-03", "NPCA", "SEONGNAM POINT LEAGUE"),
    ("2026-05-09", "PCA", "GIMPO POINT LEAGUE"), ("2026-05-10", "NPCA", "GIMPO POINT LEAGUE"),
    ("2026-05-16", "PCA", "DAEGU POINT LEAGUE"), ("2026-05-17", "NPCA", "DAEGU POINT LEAGUE"),
    ("2026-05-23", "PCA", "GIMHAE POINT LEAGUE"), ("2026-05-24", "NPCA", "GIMHAE POINT LEAGUE"),
    ("2026-05-30", "PCA", "JEJU POINT LEAGUE"), ("2026-05-31", "NPCA", "JEJU POINT LEAGUE"),
    ("2026-06-06", "PCA", "HWASEONG POINT LEAGUE"), ("2026-06-07", "NPCA", "HWASEONG POINT LEAGUE"),
    ("2026-06-13", "PCA", "INCHEON POINT LEAGUE"), ("2026-06-14", "NPCA", "INCHEON POINT LEAGUE"),
    ("2026-06-20", "PCA", "DAEJEON POINT LEAGUE"), ("2026-06-21", "NPCA", "DAEJEON POINT LEAGUE"),
    ("2026-06-27", "PCA", "YANGSAN POINT LEAGUE"), ("2026-06-28", "NPCA", "YANGSAN POINT LEAGUE"),
]


def crawl():
    out = []
    for d, fed, name in TABLE:
        slug = "asian" if "아시안" in name else name.split()[0].lower()
        out.append({"id": f"pca_table-{fed.lower()}-{d}-{slug}", "fed": fed, "date": d, "end": None,
                    "name": name, "country": "KR", "tier": "national", "host": "PCA KOREA",
                    "major": "아시안" in name, "unofficial": True, "srcNote": NOTE,
                    "regUrl": "https://coachn.co.kr/sub/competitions_list.php"})
    return out
