#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Большой аудит базы: ищет мусор, обрывки, логические противоречия, проблемы единиц."""
import json, re
from collections import Counter, defaultdict

D = json.load(open('products_inline.json', encoding='utf-8'))
byid = {x['id']: x for x in D}
issues = defaultdict(list)   # категория -> [(id, name, detail)]

SECTION_WORDS = ['характеристик', 'преимуществ', 'дополнительны', 'назначени', 'особенности', 'опции']
SENTENCE_WORDS = ['позволя', 'обеспечива', 'облегча', 'гарантир', 'подойдёт', 'подойдет', 'идеальн', 'предназнач']

def digit(v): return bool(re.search(r'\d', v))

for p in D:
    pid, nm = p['id'], p['name'][:45]
    specs = p['specs']

    # --- дубли меток в таблице ---
    tt = [s['t'] for s in specs]
    dup = [k for k, c in Counter(tt).items() if c > 1]
    if dup:
        issues['Дубли меток в таблице'].append((pid, nm, dup))

    for s in specs:
        t, v = s['t'], str(s['v']).strip()
        low = v.lower()
        # --- пустое значение ---
        if not v:
            issues['Пустое значение'].append((pid, nm, t)); continue
        # --- метка просочилась в значение (двоеточие) ---
        if ':' in v:
            issues['Двоеточие в значении (мусор)'].append((pid, nm, f'{t} = {v}'))
        # --- заголовок раздела в значении ---
        if any(w in low for w in SECTION_WORDS):
            issues['Заголовок раздела в значении'].append((pid, nm, f'{t} = {v}'))
        # --- значение = предложение ---
        if any(w in low for w in SENTENCE_WORDS) or len(v) > 55:
            issues['Значение похоже на предложение'].append((pid, nm, f'{t} = {v[:60]}'))
        # --- числовое поле без цифры ---
        if (', кг' in t or ', мм' in t or 'м²' in t) and not digit(v):
            issues['Числовое поле без числа'].append((pid, nm, f'{t} = {v}'))
        # --- поле мм с явной единицей внутри (задвоение) ---
        if ', мм' in t and re.search(r'\d\s*мм\b', v):
            issues['Единица задвоена (мм в значении)'].append((pid, nm, f'{t} = {v}'))
        if ', кг' in t and re.search(r'\d\s*кг\b', v):
            issues['Единица задвоена (кг в значении)'].append((pid, nm, f'{t} = {v}'))
        # --- габариты: допустимо N×N (2D) и N×N×N; ругаемся только на мусор ---
        if t in ('Размеры кузова, мм', 'Габаритные размеры, мм') and not re.fullmatch(r'\d+(?:×\d+){1,2}', v):
            issues['Габариты — мусор в значении'].append((pid, nm, f'{t} = {v}'))
        # --- обрывок (кончается на предлог/дефис) ---
        if re.search(r'(?:\bс|\bна|\bи|\bдля|—|-)\s*$', v):
            issues['Похоже на обрывок'].append((pid, nm, f'{t} = {v}'))

    # --- логика: грузоп > масса ---
    if p.get('gruz') and p.get('massa') and p['gruz'] > p['massa']:
        issues['Грузоп. > полной массы (невозможно)'].append((pid, nm, f"груз {p['gruz']} > масса {p['massa']}"))

    # --- тормоз bool vs spec ---
    tsp = next((s['v'] for s in specs if s['t'] == 'Тормоз'), None)
    if tsp is not None:
        spec_nobrake = (str(tsp).strip().lower() == 'нет')
        if spec_nobrake and p['brake']:
            issues['Тормоз: таблица=нет, фильтр=есть'].append((pid, nm, tsp))
        if (not spec_nobrake) and (not p['brake']):
            issues['Тормоз: таблица=есть, фильтр=нет'].append((pid, nm, tsp))

    # --- оси bool vs spec ---
    asp = next((s['v'] for s in specs if s['t'] == 'Количество осей'), None)
    if asp and p.get('axes'):
        m = re.search(r'\d', str(asp))
        if m and int(m.group()) != p['axes'] and not (p['axes'] >= 3 and int(m.group()) >= 3):
            issues['Оси: таблица ≠ фильтр'].append((pid, nm, f"таблица {asp} vs фильтр {p['axes']}"))

    # --- массКат vs масса ---
    if p.get('massa'):
        exp = '750' if p['massa'] <= 750 else '3500' if p['massa'] <= 3500 else 'hi'
        if p.get('massCat') != exp:
            issues['massCat не соответствует массе'].append((pid, nm, f"масса {p['massa']} -> {p.get('massCat')} (ожид. {exp})"))

    # --- фото ---
    if not p.get('img'):
        issues['Нет фото (img)'].append((pid, nm, ''))
    if not p.get('imgs'):
        issues['Пустой массив imgs'].append((pid, nm, ''))

    # --- цена ---
    if p.get('price') is not None and p['price'] < 3000:
        issues['Подозрительно низкая цена'].append((pid, nm, p['price']))

    # --- описание содержит спек-дамп ---
    ab = (p.get('about') or '').lower()
    if 'технические характеристики' in ab or 'основные характеристики' in ab:
        issues['Описание содержит спек-дамп'].append((pid, nm, ''))
    if len(p.get('about') or '') > 700:
        issues['Слишком длинное описание'].append((pid, nm, len(p['about'])))

    # --- преимущества: спек/заголовок/двоеточие ---
    for pr in (p.get('pros') or []):
        prl = pr.lower()
        if re.match(r'^[А-ЯЁA-Za-zА-яё][^:]{1,40}:\s*\S', pr) and any(ch.isdigit() for ch in pr):
            issues['Преимущество похоже на спек'].append((pid, nm, pr[:55]))
            break
        if re.match(r'^(по назначению|назначение|дополнительные опции|технические характеристики|основные характеристики)\b', prl):
            issues['Преимущество — заголовок раздела'].append((pid, nm, pr[:55]))
            break

    # --- нет ни одной характеристики (кроме аксессуаров) ---
    if len(specs) == 0:
        issues['Пустая таблица характеристик'].append((pid, nm, p['kind']))

# ---- ОТЧЁТ ----
print('=' * 70)
print(f'АУДИТ БАЗЫ: {len(D)} товаров')
print('=' * 70)
order = sorted(issues.keys(), key=lambda k: -len(issues[k]))
if not order:
    print('Проблем не найдено.')
for cat in order:
    lst = issues[cat]
    print(f'\n■ {cat}: {len(lst)}')
    for pid, nm, det in lst[:6]:
        print(f'    [{pid}] {nm} — {det}')
    if len(lst) > 6:
        print(f'    … ещё {len(lst)-6}')

print('\n' + '=' * 70)
print('ИТОГО категорий проблем:', len(issues), '| всего срабатываний:', sum(len(v) for v in issues.values()))
