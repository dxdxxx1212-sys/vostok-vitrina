#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Готовит данные для нового каталога из catalog.json.
Выводит products_inline.json — массив товаров с производными фасетами для фильтров.
Описания генерируются из фактов (характеристик), маркетинговый текст источника не копируется.
"""
import json, re
from collections import Counter

# --- ЧПУ-слаги: ссылка из ключевых слов позиции вместо набора цифр ---
_TRANSMAP = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'c','ч':'ch','ш':'sh','щ':'sch',
    'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}

def translit(s):
    return ''.join(_TRANSMAP.get(ch, ch) for ch in str(s).lower())

def slugify(name, brand, maxlen=60):
    """Читаемый слаг из ключевых слов позиции. Бренд впереди, если его нет в названии."""
    base = name
    b = (brand or '').strip()
    if b and b.lower() != 'другой' and b.lower() not in name.lower():
        base = b + ' ' + name
    s = translit(base)
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    if len(s) > maxlen:                     # режем по границе слова, не посреди
        cut = s[:maxlen].rsplit('-', 1)[0]
        s = cut or s[:maxlen]
    return s or 'pricep'

def assign_slugs(items):
    """Проставляет уникальные slug'и в порядке отображения (стабильно)."""
    seen = {}
    for it in items:
        base = slugify(it['name'], it['brand'])
        slug = base
        if slug in seen:
            seen[base] += 1
            slug = f'{base}-{seen[base]}'
        else:
            seen[base] = 1
        it['slug'] = slug

d = json.load(open('catalog.json', encoding='utf-8'))
try:
    RICH = json.load(open('rich_scrape.json', encoding='utf-8'))
except FileNotFoundError:
    RICH = {}

def getc(p, *keys):
    for c in p['characteristics']:
        for k in keys:
            if k.lower() in c['title'].lower():
                return c['value']
    return None

def num(s):
    if not s:
        return None
    m = re.search(r'(\d[\d\s ]*)', str(s).replace(' ', ' '))
    return int(m.group(1).replace(' ', '')) if m else None

def kind_of(p):
    n = p['name'].lower()
    if 'полуприцеп' in n: return 'Полуприцеп'
    if 'эвакуатор' in n: return 'Эвакуатор'
    if 'самосвал' in n: return 'Самосвальный'
    if any(w in n for w in ['лодоч', 'катер', 'гидроцикл', 'плавсред', 'водн', 'яхт']): return 'Лодочный'
    if any(w in n for w in ['мото', 'снегоход', 'квадро', 'багги']): return 'Для мототехники'
    if 'платформ' in n: return 'Платформа'
    if any(w in n for w in ['фургон', 'изотерм', 'рефриж']): return 'Фургон'
    if any(w in n for w in ['дом на колес', 'дом на колёс', 'кемпер', 'караван', 'автодом', 'палатка']): return 'Дом на колёсах'
    if 'коневоз' in n or 'конево' in n: return 'Коневоз'
    if 'тент' in n: return 'С тентом'
    if 'крышк' in n or 'кофр' in n: return 'С крышкой'
    if any(w in n for w in ['колесо', 'запаск', 'опорн', 'крепление', 'лебёдк', 'лебедк', 'домкрат', 'аксессуар']): return 'Аксессуар'
    if 'коммерч' in n: return 'Коммерческий'
    return 'Бортовой'

def reclassify(kind, name):
    """Точечная коррекция категории для явных «самозванцев» (аксессуары, кемперы, тяжёлая коммерция)."""
    n = name.lower()
    if kind == 'Полуприцеп':   # полуприцеп — корректный отдельный тип, не трогаем
        return kind
    # аксессуары/оснастка — сам товар, а не прицеп
    if re.match(r'^\s*(трап|сходн|аппарел|опорн)', n): return 'Аксессуар'
    if 'подкатное' in n: return 'Аксессуар'
    if 'тележк' in n and ('хранени' in n or 'напольн' in n): return 'Аксессуар'
    # кемперы / дома на колёсах (но НЕ мото-фургоны с «Автодом» в названии модели)
    if re.search(r'grasshopper|karso|\bкемпер|caravan', n) and 'мото' not in n: return 'Дом на колёсах'
    # тяжёлая коммерция / магистральные
    if re.search(r'krone|schmitz|faymonville|grunwald|wagnermaier|bonum|cool liner|лесовоз|сортиментовоз|зерновоз|контейнеровоз|пухтовоз|для леса|\bшасси\b', n): return 'Коммерческий'
    if re.search(r'тонар\s*(?:97|r3|t4|r-?3|\d{4})', n): return 'Коммерческий'
    if re.search(r'бортов\w*\s+(?:трехосн|трёхосн)', n): return 'Коммерческий'   # 3-осный = тяжёлый
    # платформы / лафеты
    if re.search(r'лафет|hulco|medax|plateau', n): return 'Платформа'
    return kind

def axes_of(p, massa):
    a = getc(p, 'количество осей', 'колесная формула', 'колёсная формула')
    if a:
        m = re.search(r'(\d)', str(a))
        if m:
            v = int(m.group(1))
            return min(v, 3) if v else None
    n = p['name'].lower()
    if any(w in n for w in ['трёхос', 'трехос', '3-х ос', '3 ос', 'трехосн', 'трёхосн']): return 3
    if any(w in n for w in ['двухос', 'двуос', '2-х ос', '2 ос', 'двуось', 'двухосн']): return 2
    if any(w in n for w in ['одноос', '1 ос', 'одноось', 'одноосн']): return 1
    # fallback по полной массе (для лёгких прицепов надёжно)
    if massa:
        if massa <= 750: return 1
        if massa <= 3500: return 2
        return 3
    return None

def brake_of(p, massa):
    b = getc(p, 'тормоз')
    if b:
        return 'без' not in b.lower() and 'нет' not in b.lower()
    if 'тормоз' in p['name'].lower():
        return True
    if massa and massa > 750:
        return True
    return False

def gen_descr(p, kind, axes, massa, gruz):
    seg = []
    base = ('Двухосный' if axes == 2 else 'Трёхосный' if axes == 3 else 'Одноосный') if axes else 'Прицеп'
    tail = {
        'С тентом': ' прицеп с тентом', 'С крышкой': ' прицеп с жёсткой крышкой',
        'Платформа': ' прицеп-платформа', 'Лодочный': ' прицеп для лодок и катеров',
        'Для мототехники': ' прицеп для мототехники', 'Самосвальный': ' самосвальный прицеп',
        'Фургон': '-фургон', 'Полуприцеп': ' — полуприцеп', 'Эвакуатор': ' — эвакуатор',
        'Коневоз': ' — коневоз', 'Дом на колёсах': ' — дом на колёсах',
        'Бортовой': ' бортовой прицеп', 'Коммерческий': ' грузовой прицеп', 'Аксессуар': '',
    }.get(kind, ' прицеп')
    if axes:
        seg.append((base + tail).strip().capitalize() + '.')
    nums = []
    if gruz: nums.append(f'грузоподъёмность {gruz} кг')
    if massa: nums.append(f'полная масса {massa} кг')
    if nums:
        s = ', '.join(nums); seg.append(s[0].upper() + s[1:] + '.')
    kuz = getc(p, 'размеры кузова', 'размеры платформы', 'длина кузова')
    if kuz:
        seg.append(f'Размеры кузова {kuz.strip()}.')
    susp = getc(p, 'подвеска')
    if susp:
        seg.append(f'Подвеска: {susp.strip().lower()}.')
    return ' '.join(seg).strip()

try:
    NORM = json.load(open('normalized.json', encoding='utf-8'))
except FileNotFoundError:
    NORM = {}

out = []
for p in d:
    pid = str(p['id'])
    nm = NORM.get(pid) or {}
    kind = reclassify(kind_of(p), p['name'])
    # факты берём из нормализованных данных, иначе — из старой деривации
    massa = nm.get('massa') if nm.get('massa') else num(getc(p, 'полная масса'))
    gruz = nm.get('gruz') if nm.get('gruz') else num(getc(p, 'грузоподъёмность', 'грузоподъемность'))
    axes = nm.get('axes') if nm.get('axes') else axes_of(p, massa)
    brake = nm['brake'] if 'brake' in nm else brake_of(p, massa)
    price = p['price'] if (p['price'] and p['price'] >= 1000) else None
    brand = (p['brand'] or '').strip() or 'Другой'
    mass_cat = None
    if massa:
        mass_cat = '750' if massa <= 750 else '3500' if massa <= 3500 else 'hi'
    # единая нормализованная таблица характеристик (без повторов)
    specs = nm.get('specs') or [{'t': c['title'], 'v': c['value']} for c in p['characteristics']]
    spd = {s['t']: str(s['v']).lower() for s in specs}
    nlow = p['name'].lower()
    # подвеска (класс)
    sv = spd.get('Подвеска', '')
    susp = ('pnevmo' if 'пневм' in sv else 'balansir' if 'балансир' in sv
            else 'torsion' if ('торсион' in sv or 'независим' in sv)
            else 'ressor' if 'рессор' in sv else None)
    # самосвал (опрокидывание) — из спеки/категории/названия
    dump = (spd.get('Самосвал') == 'да') or (kind == 'Самосвальный') or ('самосвал' in nlow)
    # оцинковка
    galv = any('цинк' in spd.get(k, '') or 'оцинк' in spd.get(k, '')
               for k in ('Защитное покрытие', 'Покрытие бортов', 'Покрытие рамы', 'Тип прицепа')) \
           or 'оцинков' in nlow
    rec = {
        'id': pid,
        'name': p['name'],
        'brand': brand,
        'kind': kind,
        'price': price,
        'old': p['old'] if p['old'] and (not price or p['old'] > price) else None,
        'axes': axes,
        'massa': massa,
        'massCat': mass_cat,
        'gruz': gruz,
        'brake': brake,
        'img': (p['media'][0] if p['media'] else ''),
        'imgs': p['media'],
        'about': nm.get('about') or gen_descr(p, kind, axes, massa, gruz),
        'pros': nm.get('pros') or [],
        'specs': specs,
        'susp': susp,
        'dump': dump,
        'galv': galv,
    }
    out.append(rec)

# сортировка: сначала с ценой (по возрастанию), потом без цены
out.sort(key=lambda x: (x['price'] is None, x['price'] or 0))
assign_slugs(out)  # ЧПУ-ссылки после сортировки — стабильны относительно порядка показа

json.dump(out, open('products_inline.json', 'w', encoding='utf-8'), ensure_ascii=False)

print('товаров:', len(out))
print('категории:', dict(Counter(x['kind'] for x in out).most_common()))
print('оси:', dict(Counter(x['axes'] for x in out).most_common()))
print('масса-кат:', dict(Counter(x['massCat'] for x in out).most_common()))
print('тормоз:', dict(Counter(x['brake'] for x in out).most_common()))
print('брендов:', len(set(x['brand'] for x in out)))
print('без цены:', sum(1 for x in out if not x['price']))
print('пример about:', out[len(out)//2]['about'][:80])