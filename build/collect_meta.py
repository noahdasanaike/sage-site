"""Snapshot per-country metadata for the site from the SAGE working files.

Reads G:/sage/README.md (coverage table: unit type, election types) and the codebook
notes.xlsx / sources.xlsx, and writes src/country_meta.json. Rerun when those change.
"""
import json, os, re
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src')
CB = 'G:/Elections Dataset/Codebook'

lines = open('G:/sage/README.md', encoding='utf-8').read().split('\n')
start = next(i for i, l in enumerate(lines) if l.startswith('## SAGE Country Coverage'))
end = next(i for i, l in enumerate(lines) if i > start and l.startswith('## '))
rows = [l for l in lines[start:end] if l.startswith('|')]
header = [c.strip() for c in rows[0].strip('|').split('|')]
meta = {}
for l in rows[2:]:
    cells = [c.strip() for c in l.strip().strip('|').split('|')]
    r = dict(zip(header, cells))
    meta[r['Country']] = {'unit': r.get('Smallest Physical Unit (Data)', ''),
                          'election_types': r.get('Election Types', '')}

units = pd.read_excel(f'{CB}/units.xlsx')
for _, r in units.iterrows():
    meta.setdefault(r.Country, {}).setdefault('unit', r['Smallest Physical Unit (Data)'])
    if not meta[r.Country].get('unit'):
        meta[r.Country]['unit'] = r['Smallest Physical Unit (Data)']
src = pd.read_excel(f'{CB}/sources.xlsx')
for c, g in src.groupby('Country'):
    meta.setdefault(c, {})['sources'] = [str(s).strip() for s in g.Source if str(s).strip() and str(s) != 'nan']
notes = pd.read_excel(f'{CB}/notes.xlsx')
for c, g in notes.groupby('Country'):
    meta.setdefault(c, {})['notes'] = [str(s).strip() for s in g.Note if str(s).strip() and str(s) != 'nan']

os.makedirs(SRC, exist_ok=True)
json.dump(meta, open(os.path.join(SRC, 'country_meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(meta), 'entries')
print(sorted({m.get('unit', '') for m in meta.values()}))
