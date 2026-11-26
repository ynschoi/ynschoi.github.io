#!/usr/bin/env python3
"""app.html(아티팩트용, 문서 골격 없음) → index.html(GitHub Pages용, 골격 추가)."""
import os
here = os.path.dirname(os.path.abspath(__file__))
body = open(os.path.join(here, "app.html"), encoding="utf-8").read()
head = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        '<meta name="description" content="BoCal — 보디빌딩 대회 캘린더. 국내·해외 대회 일정, 연맹 공식 사이트에서 매주 자동 수집">\n'
        '<meta name="apple-mobile-web-app-title" content="BoCal">\n<meta name="theme-color" content="#f6f3ee">\n<link rel="manifest" href="manifest.webmanifest">\n'
        '<link rel="icon" href="icon.svg" type="image/svg+xml">\n<link rel="apple-touch-icon" href="icon.svg">\n'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0}[hidden]{display:none!important}img{max-width:100%}</style>\n</head>\n<body>\n')
open(os.path.join(here, "index.html"), "w", encoding="utf-8").write(head + body + "\n</body>\n</html>\n")
print("index.html 생성")
