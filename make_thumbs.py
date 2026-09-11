# -*- coding: utf-8 -*-
"""Генерит лёгкие превью для фото: <path>_t.webp (max 480px, webp q72).
Нужно для сетки каталога и ленты миниатюр в модалке — чтобы мобилка не тянула
полноразмерные фото. Полное фото остаётся для главного вида в карточке товара.
Идемпотентно: уже существующее свежее превью пропускается.
"""
import json, os
from PIL import Image

MAXW = 480
Q = 72
src = json.load(open('products_inline.json', encoding='utf-8'))

# собираем все реально используемые фото (без дублей)
paths = []
seen = set()
for p in src:
    for m in (p.get('imgs') or []):
        if m and m not in seen and os.path.exists(m):
            seen.add(m); paths.append(m)

def thumb_path(m):
    base, _ = os.path.splitext(m)
    return base + '_t.webp'

made = skipped = failed = 0
saved_bytes = orig_bytes = 0
for m in paths:
    tp = thumb_path(m)
    if os.path.exists(tp) and os.path.getmtime(tp) >= os.path.getmtime(m):
        skipped += 1
        continue
    try:
        im = Image.open(m)
        im = im.convert('RGB')
        if im.width > MAXW:
            h = round(im.height * MAXW / im.width)
            im = im.resize((MAXW, h), Image.LANCZOS)
        im.save(tp, 'WEBP', quality=Q, method=6)
        made += 1
        orig_bytes += os.path.getsize(m); saved_bytes += os.path.getsize(tp)
    except Exception as e:
        failed += 1
        print('  ! fail', m, e)

print(f'превью: создано {made}, пропущено {skipped}, ошибок {failed}, всего фото {len(paths)}')
if made:
    print(f'  средний размер превью: {saved_bytes/made/1024:.0f} КБ (оригиналы в среднем {orig_bytes/made/1024:.0f} КБ)')
