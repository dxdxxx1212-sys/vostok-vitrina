#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Быстрое ПАРАЛЛЕЛЬНОЕ скачивание всех фото в media/<id>/NN.ext.
Готовые файлы пропускает (докачка). По завершении переписывает пути в catalog.json.
"""
import json, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
data = json.load(open('catalog_raw.json', encoding='utf-8'))
os.makedirs('media', exist_ok=True)

def ext_of(url):
    m = re.search(r'\.(jpg|jpeg|png|webp|gif)(?:\?|$)', url, re.I)
    return ('.' + m.group(1).lower()) if m else '.jpg'

# план: (url, path) для всего, чего нет на диске
jobs = []
for p in data:
    pid = str(p['id'])
    folder = os.path.join('media', pid)
    os.makedirs(folder, exist_ok=True)
    local = []
    for k, url in enumerate(p.get('imgs', []), 1):
        fname = f'{k:02d}{ext_of(url)}'
        path = os.path.join(folder, fname)
        local.append(f'media/{pid}/{fname}')
        if not (os.path.exists(path) and os.path.getsize(path) > 400):
            jobs.append((url, path))
    p['media'] = local

print(f'Всего фото: {sum(len(p["imgs"]) for p in data)} | докачать: {len(jobs)}')

def fetch(job):
    url, path = job
    for t in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                b = r.read()
            if len(b) < 400:
                raise ValueError('small')
            with open(path, 'wb') as f:
                f.write(b)
            return True
        except Exception:
            continue
    return False

ok = fail = done = 0
fails = []
with ThreadPoolExecutor(max_workers=16) as ex:
    futs = {ex.submit(fetch, j): j for j in jobs}
    for fut in as_completed(futs):
        done += 1
        if fut.result():
            ok += 1
        else:
            fail += 1; fails.append(futs[fut][0])
        if done % 100 == 0 or done == len(jobs):
            print(f'  {done}/{len(jobs)} — ok={ok} fail={fail}', flush=True)

json.dump(data, open('catalog.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
on_disk = sum(1 for p in data for m in p['media'] if os.path.exists(m) and os.path.getsize(m) > 400)
print(f'\nГОТОВО. Докачано: {ok}, ошибок: {fail}')
print(f'Фото на диске: {on_disk} / {sum(len(p["imgs"]) for p in data)}')
print('catalog.json обновлён.')
if fails:
    json.dump(fails, open('media_fails.json', 'w'), ensure_ascii=False, indent=1)
    print('Список неудачных -> media_fails.json')
