#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Скачивает ВСЕ фото каждой карточки локально в media/<id>/NN.ext
и переписывает пути в catalog.json на локальные (media/<id>/NN.ext).
Источник: catalog_raw.json (данные с полным списком ссылок на фото).
Самодостаточно, ни от каких других проектов не зависит.
"""
import json, os, time, re
import urllib.request, urllib.error

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
data = json.load(open('catalog_raw.json', encoding='utf-8'))
os.makedirs('media', exist_ok=True)

def ext_of(url):
    m = re.search(r'\.(jpg|jpeg|png|webp|gif)(?:\?|$)', url, re.I)
    return ('.' + m.group(1).lower()) if m else '.jpg'

def download(url, path, tries=4):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                b = r.read()
            if len(b) < 400:      # битый/заглушка
                raise ValueError('too small')
            with open(path, 'wb') as f:
                f.write(b)
            return len(b)
        except Exception:
            if t == tries - 1:
                return 0
            time.sleep(1.0 * (t + 1))
    return 0

total_ok = 0
total_fail = 0
for n, p in enumerate(data, 1):
    pid = str(p['id'])
    folder = os.path.join('media', pid)
    os.makedirs(folder, exist_ok=True)
    local = []
    for k, url in enumerate(p.get('imgs', []), 1):
        fname = f'{k:02d}{ext_of(url)}'
        path = os.path.join(folder, fname)
        if os.path.exists(path) and os.path.getsize(path) > 400:
            local.append(f'media/{pid}/{fname}'); total_ok += 1; continue
        sz = download(url, path)
        if sz:
            local.append(f'media/{pid}/{fname}'); total_ok += 1
        else:
            total_fail += 1
            print(f'  FAIL img {url}', flush=True)
        time.sleep(0.12)
    p['media'] = local          # локальные пути ко всем фото
    if n % 25 == 0 or n == len(data):
        print(f'[{n}/{len(data)}] {pid} — {len(local)} фото | ok={total_ok} fail={total_fail}', flush=True)

json.dump(data, open('catalog.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\nГОТОВО. Скачано фото: {total_ok}, не удалось: {total_fail}')
print(f'catalog.json обновлён (поле media = локальные пути).')
