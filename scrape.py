#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Полный парс всех карточек центр-прицепов.рф/alltrailers.
Из каждой детальной страницы берём inline `var product = {...}`:
имя, бренд, цена/старая цена, sku, ВСЮ галерею фото, описание, характеристики.
Результат -> catalog_raw.json (структурировано).
"""
import json, re, time, sys, html as htmllib
import urllib.request, urllib.error

SRC = json.load(open('product_list.json', encoding='utf-8'))
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'

def fetch(url, tries=4):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'ru,en'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:
            if t == tries - 1:
                return None
            time.sleep(1.2 * (t + 1))
    return None

def extract_product(h):
    """Достаём сбалансированный JSON-объект из `var product = {...}`."""
    i = h.find('var product = ')
    if i < 0:
        return None
    seg = h[i + len('var product = '):]
    depth = 0; start = None; instr = False; esc = False
    for j, ch in enumerate(seg):
        if esc:
            esc = False; continue
        if ch == '\\':
            esc = True; continue
        if ch == '"':
            instr = not instr; continue
        if instr:
            continue
        if ch == '{':
            if depth == 0:
                start = j
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(seg[start:j + 1])
                except Exception:
                    return None
    return None

def strip_html(s):
    if not s:
        return ''
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'</p>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    s = htmllib.unescape(s)
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

def norm_price(v):
    if v in (None, '', '0', 0):
        return None
    try:
        return int(round(float(str(v).replace(' ', '').replace(',', '.'))))
    except Exception:
        return None

out = []
fails = []
for n, item in enumerate(SRC, 1):
    url = item['link']
    h = fetch(url)
    if not h:
        fails.append(url); print(f'[{n}/{len(SRC)}] FAIL fetch {url}', flush=True); continue
    p = extract_product(h)
    if not p:
        fails.append(url); print(f'[{n}/{len(SRC)}] FAIL parse {url}', flush=True); continue

    imgs = []
    for g in (p.get('gallery') or []):
        u = g.get('img') if isinstance(g, dict) else None
        if u and u not in imgs:
            imgs.append(u)
    chars = []
    for c in (p.get('characteristics') or []):
        t = (c.get('title') or '').strip()
        v = (c.get('value') or '').strip()
        if t:
            chars.append({'title': t, 'value': v})

    rec = {
        'id': str(p.get('uid') or item.get('link').split('/')[-1].split('-')[0]),
        'name': (p.get('title') or item['name']).strip(),
        'brand': (p.get('brand') or '').strip(),
        'price': norm_price(p.get('price')) or item.get('price'),
        'old': norm_price(p.get('priceOld')),
        'sku': (p.get('sku') or '').strip(),
        'url': p.get('url') or url,
        'imgs': imgs,
        'descr': strip_html(p.get('text')),
        'specs': [f"{c['title']}: {c['value']}".strip().rstrip(':') for c in chars],
        'characteristics': chars,
    }
    out.append(rec)
    if n % 25 == 0 or n == len(SRC):
        print(f'[{n}/{len(SRC)}] ok — {rec["name"][:40]} | imgs={len(imgs)} specs={len(chars)}', flush=True)
    time.sleep(0.35)

json.dump(out, open('catalog_raw.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
tot_imgs = sum(len(x['imgs']) for x in out)
multi = sum(1 for x in out if len(x['imgs']) > 1)
print(f'\nГОТОВО: {len(out)}/{len(SRC)} карточек -> catalog_raw.json')
print(f'Всего фото: {tot_imgs} | карточек с >1 фото: {multi} | без фото: {sum(1 for x in out if not x["imgs"])}')
print(f'Не удалось: {len(fails)}')
if fails:
    json.dump(fails, open('scrape_fails.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
