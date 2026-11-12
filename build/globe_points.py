"""Sample geocoded unit centroids from released SAGE data for the homepage globe.
Latest year per country; distinct units (lat/lon to 0.01 deg); 40k points total, at least 150 per country.
Output: sage-site/data/globe_points.bin, little-endian Int16 pairs (lon*180, lat*360);
the site loads it as data/globe_points.js (window.SAGE_GLOBE = base64 of the .bin)."""
import os, random, struct
import pyarrow.dataset as ds
import pyarrow.compute as pc

ROOT = 'J:/sage_v2_work/released_mirror/parquet'
OUT = 'C:/Users/Noah/Documents/Github/sage-site/data/globe_points.bin'
TOTAL, FLOOR = 40000, 150
random.seed(1)

per = {}
for cdir in sorted(os.listdir(ROOT)):
    if not cdir.startswith('country='):
        continue
    years = sorted(int(y.split('=')[1]) for y in os.listdir(f'{ROOT}/{cdir}') if y.startswith('year='))
    pts = set()
    for y in reversed(years):
        t = ds.dataset(f'{ROOT}/{cdir}/year={y}', format='parquet').to_table(columns=['latitude', 'longitude'])
        la, lo = t['latitude'].to_pylist(), t['longitude'].to_pylist()
        pts = {(round(a, 2), round(b, 2)) for a, b in zip(la, lo)
               if a is not None and b is not None and -90 <= a <= 90 and -180 <= b <= 180 and (a, b) != (0, 0)}
        if pts:
            break
    if pts:
        per[cdir[8:]] = list(pts)

n = sum(len(v) for v in per.values())
out = []
for c, v in per.items():
    k = min(len(v), max(FLOOR, round(TOTAL * len(v) / n)))
    out += random.sample(v, k)
random.shuffle(out)
with open(OUT, 'wb') as f:
    for la, lo in out:
        f.write(struct.pack('<hh', round(lo * 180), round(la * 360)))
print(len(per), 'countries', n, 'distinct units', len(out), 'points', os.path.getsize(OUT), 'bytes')
