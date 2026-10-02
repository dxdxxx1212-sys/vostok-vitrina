#!/usr/bin/env python3
"""Собирает index.html из site_template.html + products_inline.json.

Чтобы страница открывалась быстро, в index.html встраивается только лёгкий список
(сетка, фильтры, поиск). Тяжёлые поля окна товара (описание, плюсы, характеристики,
все фото) уходят в details.json — его страница догружает сама после показа каталога.
products_inline.json остаётся полным (его читают подборки и make_table.py).

Запуск: python3 assemble.py   (после build_site.py)
"""
import hashlib, json

HEAVY = ('about', 'pros', 'specs', 'imgs', 'thumbs')

items = json.load(open('products_inline.json', encoding='utf-8'))
dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))

light = [{k: v for k, v in p.items() if k not in HEAVY} for p in items]
details = {p['id']: [p.get(k) for k in HEAVY] for p in items}

det = dump(details)
open('details.json', 'w', encoding='utf-8').write(det)
ver = hashlib.md5(det.encode()).hexdigest()[:8]   # ?v= меняется только когда меняются данные

t = open('site_template.html', encoding='utf-8').read()
assert t.count('__DATA__') == 1 and t.count('__DETAILS_URL__') == 1
html = t.replace('__DATA__', dump(light), 1).replace('__DETAILS_URL__', 'details.json?v=' + ver, 1)
open('index.html', 'w', encoding='utf-8').write(html)
print(f'index.html {len(html.encode())//1024} КБ, details.json {len(det.encode())//1024} КБ, v={ver}')
