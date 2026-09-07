#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Повторный полный парс: аккуратно вытаскиваем ПОЛНОЕ описание и все техпункты.
Правильно обрабатываем <li>/<ul>/<strong>. Мёржим в catalog.json (media не трогаем).
Выход: обогащённые поля descr (полный текст), techlist (буллеты теххарактеристик).
"""
import json, re, time, html as H
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
SRC = json.load(open('product_list.json', encoding='utf-8'))

def fetch(url, tries=4):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'ru'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception:
            if t == tries - 1:
                return None
            time.sleep(0.8 * (t + 1))
    return None

def extract_product(h):
    i = h.find('var product = ')
    if i < 0:
        return None
    seg = h[i + 14:]
    depth = 0; start = None; instr = False; esc = False
    for j, ch in enumerate(seg):
        if esc: esc = False; continue
        if ch == '\\': esc = True; continue
        if ch == '"': instr = not instr; continue
        if instr: continue
        if ch == '{':
            if depth == 0: start = j
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                try: return json.loads(seg[start:j + 1])
                except Exception: return None
    return None

def split_text(raw):
    """Возвращает (описание_текст, [техпункты])."""
    if not raw:
        return '', []
    # вытащим буллеты <li>...</li>
    lis = re.findall(r'<li[^>]*>(.*?)</li>', raw, re.S)
    def clean(s):
        s = re.sub(r'<[^>]+>', '', s)
        return re.sub(r'\s+', ' ', H.unescape(s)).strip()
    bullets = [clean(x) for x in lis if clean(x)]
    # текст без <ul>...</ul> и без списков
    txt = re.sub(r'<ul[^>]*>.*?</ul>', '\n', raw, flags=re.S)
    txt = re.sub(r'<br\s*/?>', '\n', txt)
    txt = re.sub(r'</?(p|div|strong|b|h\d)[^>]*>', '\n', txt)
    txt = re.sub(r'<[^>]+>', '', txt)
    txt = H.unescape(txt)
    txt = re.sub(r'[ \t]+', ' ', txt)
    txt = re.sub(r' *\n *', '\n', txt)
    txt = re.sub(r'\n{3,}', '\n\n', txt).strip()
    # уберём одиночный хвост "Технические характеристики:" если список ушёл в bullets
    txt = re.sub(r'\n?Технические характеристики:?\s*$', '', txt).strip()
    return txt, bullets

def norm_price(v):
    if v in (None, '', '0', 0): return None
    try: return int(round(float(str(v).replace(' ', '').replace(',', '.'))))
    except Exception: return None

def one(item):
    h = fetch(item['link'])
    if not h: return None
    p = extract_product(h)
    if not p: return None
    txt, bullets = split_text(p.get('text'))
    chars = []
    for c in (p.get('characteristics') or []):
        t = (c.get('title') or '').strip(); v = (c.get('value') or '').strip()
        if t: chars.append({'title': t, 'value': v})
    imgs = []
    for g in (p.get('gallery') or []):
        u = g.get('img') if isinstance(g, dict) else None
        if u and u not in imgs: imgs.append(u)
    return {
        'id': str(p.get('uid')),
        'name': (p.get('title') or item['name']).strip(),
        'brand': (p.get('brand') or '').strip(),
        'price': norm_price(p.get('price')) or item.get('price'),
        'old': norm_price(p.get('priceOld')),
        'url': p.get('url') or item['link'],
        'imgs': imgs,
        'descr_full': txt,             # полный маркетинговый текст + преимущества
        'techlist': bullets,           # техпункты (буллеты) — точь-в-точь как в источнике
        'characteristics': chars,      # официальные структурированные хар-ки
    }

rich = {}
fails = []
with ThreadPoolExecutor(max_workers=14) as ex:
    futs = {ex.submit(one, it): it for it in SRC}
    done = 0
    for fut in as_completed(futs):
        done += 1
        r = fut.result()
        if r: rich[r['id']] = r
        else: fails.append(futs[fut]['link'])
        if done % 50 == 0 or done == len(SRC):
            print(f'{done}/{len(SRC)} — ok={len(rich)} fail={len(fails)}', flush=True)

json.dump(rich, open('rich_scrape.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# статистика
tl = [len(r['techlist']) for r in rich.values()]
print(f'\nГОТОВО: {len(rich)} карточек')
print(f'с техсписком: {sum(1 for x in tl if x)} | среднее пунктов: {round(sum(tl)/max(1,len(tl)),1)} | макс: {max(tl) if tl else 0}')
print(f'с описанием: {sum(1 for r in rich.values() if r["descr_full"])}')
if fails:
    json.dump(fails, open('rescrape_fails.json','w'), ensure_ascii=False, indent=1)
    print('fails ->', len(fails))
