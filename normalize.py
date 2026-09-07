#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Нормализует выкачанную инфу в единую таблицу характеристик (без повторов)
+ короткое описание + список преимуществ. Пишет normalized.json {id: {...}}.
"""
import json, re
from collections import Counter

RICH = json.load(open('rich_scrape.json', encoding='utf-8'))

def clean(s):
    return re.sub(r'\s+', ' ', (s or '')).strip()

def dims(v):
    # приводим к N×N×N: убираем единицы/двоеточия, берём числа, склеиваем ×
    t = re.sub(r'(?:мм|см|\bм\b|:)', ' ', v, flags=re.I)
    t = re.sub(r'(\d)[.,](\d{3})\b', r'\1\2', t)   # 1,560 -> 1560 (разделитель тысяч)
    nums = re.findall(r'\d+', t)
    if len(nums) < 2:
        return None
    return '×'.join(nums[:3])

def intnum(v):
    m = re.search(r'(\d[\d ]*\d|\d)', v)
    return m.group(1).replace(' ', '') if m else None

# каноническая карта из структурированных характеристик
STRUCT_MAP = {
    'грузоподъёмность': 'Грузоподъёмность, кг',
    'грузоподъемность': 'Грузоподъёмность, кг',
    'полная масса': 'Полная масса, кг',
    'размеры кузова': 'Размеры кузова, мм',
    'габаритные размеры': 'Габаритные размеры, мм',
    'тип прицепа': 'Тип прицепа',
    'тип разгрузки': 'Тип разгрузки',
    'количество осей': 'Количество осей',
    'подвеска': 'Подвеска',
    'тип тормозной системы': 'Тормоз',
    'тип осей': 'Тип осей',
    'колеса': 'Колёса',
    'объем кузова': 'Объём кузова, м³',
    'длина кузова внутренняя': 'Внутренняя длина кузова, мм',
}

# добор из текста: (каноническая метка, [паттерны], тип)
EXTRA = [
    ('Грузоподъёмность, кг', [r'Грузоподъ[её]мность\D{0,6}(\d[\d ]*\d|\d)\s*кг'], 'int'),
    ('Полная масса, кг',      [r'Полная масса\D{0,6}(\d[\d ]*\d|\d)\s*кг'], 'int'),
    ('Снаряжённая масса, кг',  [r'(?:Снаряж[её]нная|Собственная) масса\D{0,6}(\d[\d ]*\d|\d)'], 'int'),
    ('Количество осей',        [r'Кол(?:ичество|-во) осей(?:/кол[её]с)?\D{0,4}(\d)'], 'axes'),
    ('Подвеска',               [r'(?:Тип подвески|Подвеска)\s*:?\s*(рессорн\w+|торсионн\w+|пружинн\w+)'], 'lower'),
    ('Пол',                    [r'Пол(?: прицепа)?\s*:?\s*(фанера|ламинирован\w+|металл\w*|доска)'], 'lower'),
    ('Самосвал',               [r'(?:Функция самосвала|Самосвал\w*)\s*:?\s*(да|нет|есть)'], 'yesno'),
    ('Высота борта',           [r'Высота борта\D{0,4}([\d.,]+)\s*м(?!м)'], 'raw_m'),
    ('Площадь пола, м²',       [r'Площадь пола(?: платформы)?\D{0,4}(\d[\d.,]*)\s*м'], 'rawf'),
    ('Погрузочная высота, мм', [r'Погрузочная высота\D{0,4}(\d+)\s*мм'], 'int'),
    ('Дорожный просвет, мм',   [r'Дорожный просвет\D{0,4}(\d+)\s*мм'], 'int'),
    ('Колея колёс, мм',        [r'Коле[яи] кол[её]с\D{0,4}(\d+)\s*мм'], 'int'),
    ('Нагрузка на ось, кг',    [r'Нагрузка на (?:одну )?ось\D{0,4}(\d[\d ]*\d|\d)'], 'int'),
    ('Листов рессоры',         [r'Кол-во листов рессоры\D{0,4}(\d+)'], 'int'),
    ('Колёса',                 [r'(?:Размер кол[её]с|Радиус колес|Кол[её]са)\s*:?\s*(R\s*\d{2})'], 'wheel'),
    ('Колёсная формула',       [r'(?:Формула колесного диска|Колесн\w+ формула|Ошиновка)\s*:?\s*([\dxх×/]+)'], 'raw'),
    ('Сцепное устройство',     [r'Сцепное устройство\D{0,4}(\d[\d ]*\d|\d)\s*кг'], 'intkg'),
    ('Тип ТСУ',                [r'Тип ТСУ\s*:?\s*(шар[^\n]{0,22})'], 'raw'),
    ('Штекер',                 [r'Штекер\s*:?\s*(\d+[\s-]?pin|\d+[\s-]?контакт\w*)'], 'raw'),
    ('Фонари',                 [r'Фонари\s*:?\s*(светодиод\w*|накал\w*|LED|галоген\w*)'], 'lower'),
    ('Петли крепления груза',  [r'Петли крепления груза\D{0,4}(\d+)\s*шт'], 'intsht'),
    ('Покрытие рамы',          [r'Покрытие рамы\s*:?\s*(цинк\w*|краск\w*|порошк\w*|оцинк\w*|грунт\w*|эмал\w*|горячее\w*)'], 'lower'),
    ('Покрытие бортов',        [r'Покрытие бортов\s*:?\s*(цинк\w*|краск\w*|порошк\w*|оцинк\w*|грунт\w*|эмал\w*|алюмин\w*)'], 'lower'),
    ('Защитное покрытие',      [r'Защитное покрытие\s*:?\s*(цинк\w*|краск\w*|порошк\w*|оцинк\w*|грунт\w*)'], 'lower'),
    ('Внутренняя длина кузова',[r'Длина (?:прицепа внутри|кузова внутренняя)\D{0,6}(до\s*[\d.,]+\s*м|[\d.,]+\s*м)'], 'raw'),
    ('Внутренняя ширина кузова',[r'Ширина (?:прицепа внутри|кузова внутренняя)\D{0,6}(до\s*[\d.,]+\s*м|[\d.,]+\s*м)'], 'raw'),
    ('Гарантия',               [r'Гарантия\s*:?\s*(\d+\s*месяц\w*|\d+\s*(?:год|года|лет))'], 'raw'),
]

# порядок вывода (основные сверху)
ORDER = ['Грузоподъёмность, кг','Полная масса, кг','Снаряжённая масса, кг','Количество осей',
    'Тормоз','Подвеска','Тип осей','Размеры кузова, мм','Габаритные размеры, мм',
    'Внутренняя длина кузова','Внутренняя ширина кузова','Объём кузова, м³','Площадь пола, м²',
    'Высота борта','Погрузочная высота, мм','Дорожный просвет, мм','Колея колёс, мм',
    'Нагрузка на ось, кг','Листов рессоры','Колёса','Колёсная формула','Сцепное устройство',
    'Тип ТСУ','Пол','Самосвал','Покрытие рамы','Покрытие бортов','Защитное покрытие',
    'Фонари','Штекер','Петли крепления груза','Тип разгрузки','Тип прицепа','Гарантия']

def fmt_val(val, typ):
    val = clean(val)
    if typ == 'int': return intnum(val)                 # единица уже в названии параметра
    if typ == 'intkg': return (intnum(val) + ' кг') if intnum(val) else None
    if typ == 'intsht': return (intnum(val) + ' шт.') if intnum(val) else None
    if typ == 'axes':
        n = intnum(val); return n if n else None
    if typ == 'lower': return val.lower()
    if typ == 'yesno':
        return 'да' if val.lower() in ('да','есть') else 'нет'
    if typ == 'raw_m': return (val + ' м') if val else None
    if typ == 'rawf': return val                        # название уже содержит «м²»
    if typ == 'wheel': return re.sub(r'\s+', '', val)
    if typ == 'raw': return val
    return val

def brake_value(text, massa):
    for pat in [r'Наличие тормоз\w*\s*:?\s*([^\n]{1,60})',
                r'Тип тормозной системы\s*:?\s*([^\n]{1,60})',
                r'(?:[•\n]|^)\s*Тормоз(?:а|ов|ные|ная система)?\b\s*:?\s*([^\n]{1,60})']:
        m = re.search(pat, text, re.I)
        if m:
            v = m.group(1).strip().lower()
            if any(w in v for w in ['нет', 'без', 'отсут', 'не пред']):
                return 'нет', False
            if any(w in v for w in ['накат', 'инерц', 'диск', 'бараб', 'гидра', 'налив', 'есть', 'да', 'пневм', 'abs', 'ebs', 'wabco', 'tebs']):
                disp = clean(m.group(1))
                disp = re.sub(r'^(?:[—–-]\s*|Тип\s*[—–:-]\s*|Тормоза?\s*:\s*)', '', disp, flags=re.I).strip(' ,—–-')
                return (disp if 2 < len(disp) <= 50 else 'есть'), True
    # нет явного поля — по полной массе (тяжелее 750 кг обычно с тормозом)
    if massa and massa > 750:
        return 'есть', True
    if massa:
        return 'нет', False
    return None, None

out = {}
for pid, p in RICH.items():
    text = '\n'.join(p['techlist']) + '\n' + \
           '\n'.join(f"{c['title']}: {c['value']}" for c in p['characteristics']) + '\n' + \
           (p.get('descr_full') or '')

    specs = {}  # label -> value

    # 1) структурированные (чистые, приоритет)
    for c in p['characteristics']:
        key = STRUCT_MAP.get(c['title'].strip().lower().rstrip(', кгмм').strip())
        # мягкий матч
        if not key:
            for k, v in STRUCT_MAP.items():
                if c['title'].strip().lower().startswith(k):
                    key = v; break
        if key and key not in specs:
            val = clean(c['value'])
            if 'мм' in key or 'Размеры' in key or 'Габаритные' in key:
                val = dims(val) or val
            specs[key] = val

    # 2) тормоз (спец-логика) — считаем массу заранее
    mm = re.search(r'Полная масса\D{0,6}(\d[\d ]*\d|\d)', text, re.I)
    massa_pre = int(mm.group(1).replace(' ', '')) if mm else None
    bt, bbool = brake_value(text, massa_pre)
    if bt:
        specs['Тормоз'] = bt   # чистое значение (перекрывает возможный мусор из структуры)

    # 3) добор остального
    for label, pats, typ in EXTRA:
        if label in specs:
            continue
        for pat in pats:
            m = re.search(pat, text, re.I)
            if m:
                v = fmt_val(m.group(1), typ)
                if v:
                    specs[label] = v
                break

    # числовые поля с одним значением -> голое число (убирает "600 кг по паспорту / ...")
    for lab in ['Грузоподъёмность, кг', 'Полная масса, кг', 'Снаряжённая масса, кг',
                'Нагрузка на ось, кг', 'Погрузочная высота, мм', 'Дорожный просвет, мм', 'Колея колёс, мм']:
        if lab in specs:
            m = re.search(r'\d[\d ]*\d|\d', specs[lab])
            if m:
                specs[lab] = m.group().replace(' ', '')

    # чистка шумных/длинных значений отдельных полей (в осн. полуприцепы из структуры)
    for lab in ['Подвеска', 'Колёса', 'Тип ТСУ', 'Тип разгрузки', 'Тип осей', 'Пол']:
        if lab in specs:
            val = re.split(r'\s*(?:/| или |\(|;)\s*', specs[lab])[0].strip(' ,.')
            if len(val) > 32:
                val = val[:32].rsplit(' ', 1)[0]
            specs[lab] = val

    # оси как число для фильтра
    axes = None
    if 'Количество осей' in specs:
        axes = int(re.search(r'\d', specs['Количество осей']).group())
        specs['Количество осей'] = str(axes) + (' ось' if axes==1 else ' оси' if axes<5 else ' осей')

    # массы/грузоп числами
    def num_of(label):
        if label in specs:
            m = re.search(r'\d[\d ]*\d|\d', specs[label])
            return int(m.group().replace(' ','')) if m else None
        return None
    massa = num_of('Полная масса, кг')
    gruz = num_of('Грузоподъёмность, кг')

    # описание: вступление (до "Преимущества"/спеков) из descr_full
    df = p.get('descr_full') or ''
    df = re.sub(r'^В наличии:[^\n]*\n?', '', df).strip()
    intro = re.split(r'\n?(?:Преимущества|Основные характеристики|Технические характеристики|Дополнительные опции|Назначение|Особенности|Гарантия|Комплектация)', df)[0].strip()
    intro = re.sub(r'\n{2,}', ' ', intro).strip()
    # обрезаем слишком длинное описание по границе предложения
    if len(intro) > 450:
        cut = intro[:450]
        dot = cut.rfind('. ')
        intro = (cut[:dot + 1] if dot > 200 else cut.rstrip(' ,') + '…')

    # преимущества: маркетинговые буллеты из techlist до первого спек-раздела
    pros = []
    for b in p['techlist']:
        bl = b.strip()
        low = bl.lower()
        if re.match(r'^(основные характеристики|технические характеристики|дополнительные опции|назначение|особенности|по назначению|гарантия)', low):
            break
        if ':' in bl:            # заголовки ("По назначению:") и спеки ("Полная масса: 750 кг")
            continue
        if len(bl) < 15 or bl.endswith(':') or len(bl) > 160:
            continue
        pros.append(bl.rstrip('.'))
        if len(pros) >= 6:
            break

    out[pid] = {
        'specs': [{'t': k, 'v': specs[k]} for k in ORDER if k in specs]
                 + [{'t': k, 'v': specs[k]} for k in specs if k not in ORDER],
        'about': intro,
        'pros': pros,
        'axes': axes, 'massa': massa, 'gruz': gruz,
        'brake': bbool if bbool is not None else (massa is not None and massa > 750),
    }

json.dump(out, open('normalized.json', 'w', encoding='utf-8'), ensure_ascii=False)
sc = [len(v['specs']) for v in out.values()]
print('товаров:', len(out))
print('среднее характеристик:', round(sum(sc)/len(sc),1), '| макс:', max(sc), '| мин:', min(sc))
print('с преимуществами:', sum(1 for v in out.values() if v['pros']))
print('с описанием:', sum(1 for v in out.values() if v['about']))
# пример
ex = [v for k,v in out.items() if k=='449432266042'][0]
print('\n=== Славич 223 ===')
print('about:', ex['about'])
print('pros:', ex['pros'])
print('specs:')
for s in ex['specs']: print('   ', s['t'], '—', s['v'])
