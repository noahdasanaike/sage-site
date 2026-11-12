"""Simplified GADM 4.1 country outlines for the homepage globe.
Output: sage-site/data/globe_countries.js setting window.SAGE_COUNTRIES, base64 of little-endian Int16:
for each ring, the point count, then (lon*180, lat*360) pairs."""
import base64, struct
import pyogrio
from shapely import simplify, get_parts, get_exterior_ring, get_coordinates

SRC = 'J:/sage_crosswalk/gadm_world/gadm_410-levels.gpkg'
OUT = 'C:/Users/Noah/Documents/Github/sage-site/data/globe_countries.js'

g = pyogrio.read_dataframe(SRC, layer='ADM_0', columns=['GID_0'])
buf = bytearray()
rings = 0
for geom in g.geometry:
    if geom is None:
        continue
    for poly in get_parts(simplify(geom, 0.15)):
        if poly.is_empty or poly.area < 0.3:
            continue
        xy = get_coordinates(get_exterior_ring(poly))
        if len(xy) < 4:
            continue
        buf += struct.pack('<h', len(xy))
        for x, y in xy:
            buf += struct.pack('<hh', round(x * 180), round(y * 360))
        rings += 1
open(OUT, 'w').write('window.SAGE_COUNTRIES="' + base64.b64encode(bytes(buf)).decode() + '";\n')
print(len(g), 'countries', rings, 'rings', len(buf), 'bytes')
