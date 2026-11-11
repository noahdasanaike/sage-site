"""Build sage-elections.com: the home page plus one page per country.

Inputs (all in this repo):
  src/home.html             home page template (the SAGE page)
  src/country_meta.json     unit type, sources and notes per country (build/collect_meta.py)
  data/sage_coverage.json   one row per contest (from the coverage build)
  data/sage_downloads.json  download paths and sizes (from build_final.py)
Outputs: index.html, style.css, <slug>/index.html, sitemap.xml, robots.txt, 404.html.

Usage: python build/build_site.py
"""
import datetime, html, json, os, re, unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SITE = 'https://sage-elections.com'
OLD = 'https://noahdasanaike.github.io'
EXPLORER = f'{OLD}/explore/'
GCS = 'https://storage.googleapis.com/sage-archive'
PAPER = 'https://www.nature.com/articles/s41597-026-07869-x'
DOI = 'https://doi.org/10.7910/DVN/YGJR1L'
TODAY = datetime.date.today().isoformat()
E = html.escape


def rd(p):
    return open(os.path.join(ROOT, p), encoding='utf-8').read()


def wr(p, s):
    p = os.path.join(ROOT, p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8', newline='\n').write(s)


def slug(name):
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def fmt_bytes(b):
    if not b:
        return ''
    if b < 1e6:
        return f'{max(1, round(b / 1e3))} KB'
    if b < 1e9:
        return f'{b / 1e6:.1f} MB' if b < 1e7 else f'{round(b / 1e6)} MB'
    return f'{b / 1e9:.1f} GB'


def gcs_url(path):
    from urllib.parse import quote
    return GCS + '/' + '/'.join(quote(seg) for seg in path.split('/'))


def unit_phrase(unit):
    """'Polling Station' -> 'polling station'; mixed descriptions -> first unit."""
    u = re.split(r'[(,]', unit)[0].strip()
    return u.lower() if u else 'smallest unit'


def plural(w):
    if w.endswith('y') and not w.endswith(('ay', 'ey', 'oy')):
        return w[:-1] + 'ies'
    if w.endswith(('s', 'x')):
        return w + 'es'
    return w + 's'


def year_list(ys):
    ys = [str(y) for y in ys]
    return ys[0] if len(ys) == 1 else ', '.join(ys[:-1]) + ' and ' + ys[-1]


# ---------------------------------------------------------------- data
cov = json.loads(rd('data/sage_coverage.json'))
ci = {c: i for i, c in enumerate(cov['columns'])}
contests = {}
for r in cov['rows']:
    contests.setdefault(r[ci['country']], []).append({c: r[i] for c, i in ci.items()})
meta = json.loads(rd('src/country_meta.json'))
downloads = json.loads(rd('data/sage_downloads.json')) if os.path.exists(os.path.join(ROOT, 'data/sage_downloads.json')) else {}
admin_dl = json.loads(rd('data/sage_admin_downloads.json')) if os.path.exists(os.path.join(ROOT, 'data/sage_admin_downloads.json')) else {}
countries = sorted(contests)
N = len(countries)

# ---------------------------------------------------------------- style.css
home = rd('src/home.html')
style = re.search(r'<style>(.*?)</style>', home, re.S).group(1)
style += """
        /* country pages */
        .crumbs { font-size: 0.9em; margin-bottom: 1em; }
        .facts { color: #444; }
        .country-index { columns: 3 12em; column-gap: 2em; line-height: 1.7; margin: 0.5em 0 1.5em; }
        .country-index a { color: #333; }
        .country-index a:hover { color: #750014; }
        table.plain { border-collapse: collapse; width: 100%; font-size: 0.88em; margin: 0.5em 0 1em; }
        table.plain th { text-align: left; background: #f9f9f9; white-space: nowrap; }
        table.plain th, table.plain td { padding: 4px 8px; border-bottom: 1px solid #f0f0f0; }
        table.plain td.num, table.plain th.num { text-align: right; font-variant-numeric: tabular-nums; }
        .table-scroll { overflow-x: auto; }
        .dl-size { color: #888; }
        td .dl { white-space: nowrap; margin-right: 6px; }
"""
wr('style.css', style)

# ---------------------------------------------------------------- home page
# Static rows for the countries table, so the page links exist without JavaScript;
# the script in the page replaces them with the sortable, expandable version.
static_rows = []
for c in countries:
    ys = sorted({r['year'] for r in contests[c]})
    span = f'{ys[0]}&ndash;{ys[-1]}' if len(ys) > 1 else f'{ys[0]}'
    static_rows.append(f'                <tr><td><a class="cov-page" href="/{slug(c)}/">{E(c)}</a></td>'
                       f'<td>{span}</td><td class="num">{len(ys)}</td><td></td><td></td><td></td>'
                       f'<td class="page-cell"><a class="page-btn" href="/{slug(c)}/"><span class="pb-long">country </span>page &rarr;</a></td></tr>')
h = home
h = re.sub(r'<title>.*?</title>',
           f'<title>Polling station election results for {N} countries | SAGE</title>', h, flags=re.S)
h = re.sub(r'<meta name="description"\s+content="[^"]*"\s*/>',
           f'<meta name="description" content="Free, geocoded election results at the polling station or '
           f'smallest published unit for {N} countries, 1948 to 2026, with boundaries. Download as CSV, '
           f'GeoPackage, Parquet or R, or load with the R and Python packages." />\n'
           f'    <link rel="canonical" href="{SITE}/" />', h, count=1)
h = h.replace('"url": "https://noahdasanaike.github.io/sage.html"', f'"url": "{SITE}/"')
h = h.replace('href="index.html"', f'href="{OLD}/"')
h = h.replace('href="posts/', f'href="{OLD}/posts/').replace('href="usa-precincts/', f'href="{OLD}/usa-precincts/')
h = h.replace('const EXPLORER_URL = "explore/";', f'const EXPLORER_URL = "{EXPLORER}";')
anchor = '<tbody id="coverage-body"></tbody>'
assert h.count(anchor) == 1
h = h.replace(anchor, '<tbody id="coverage-body">\n' + '\n'.join(static_rows) + '\n            </tbody>')
wr('index.html', h)

# ---------------------------------------------------------------- country pages
ALSO_CITE = {'Brazil', 'Afghanistan', 'Pakistan', 'Uganda', 'United States of America', 'Malaysia', 'Mexico',
             'Papua New Guinea', 'Solomon Islands', 'Russia', 'South Africa', 'Ghana', 'Zambia', 'Botswana',
             'Belgium', 'Democratic Republic of the Congo', 'Myanmar', 'Uruguay'}
CITE = ('Dasanaike, Noah. &ldquo;The Small-Area Global Elections (SAGE) Dataset.&rdquo; '
        '<em>Scientific Data</em> (2026).')


def dl_cell(f, label):
    if not f or not f.get('path'):
        return ''
    size = f' <span class="dl-size">{fmt_bytes(f.get("bytes"))}</span>' if f.get('bytes') else ''
    tgt = ' target="_blank" rel="noopener"' if f['path'].endswith('.pdf') else ''
    return f'<a class="dl" href="{gcs_url(f["path"])}"{tgt}>[{label}{size}]</a>'


def country_page(c):
    rows = sorted(contests[c], key=lambda r: (r['year'], str(r['election_type']), str(r['special_type']), r['round'] or 0))
    m = meta.get(c, {})
    unit_raw = m.get('unit', '')
    unit = unit_phrase(unit_raw)
    years = sorted({r['year'] for r in rows})
    y0, y1 = years[0], years[-1]
    span = f'{y0}&ndash;{y1}' if y0 != y1 else f'{y0}'
    span_txt = f'{y0} to {y1}' if y0 != y1 else f'{y0}'
    types = sorted({r['election_type'] for r in rows if r['election_type']})
    type_words = sorted({t.split(' (')[0].lower() for t in types})
    last = [r for r in rows if r['year'] == y1]
    top = max(last, key=lambda r: r['units'])
    poly_years = sorted({r['year'] for r in rows if r['polygons']})
    iso3 = rows[0]['iso3'] or ''

    # prose
    the = 'the ' if c.startswith(('United', 'Democratic Republic', 'Netherlands', 'Philippines', 'Gambia',
                                   'Dominican Republic', 'Maldives', 'Seychelles', 'Solomon', 'Isle of Man')) else ''
    s1 = (f'SAGE has {" and ".join(type_words)} election results for {the}{c} '
          f'{"from " + str(y0) if len(years) == 1 else "from " + str(len(years)) + " elections between " + str(y0) + " and " + str(y1)}'
          f'{"" if len(years) == 1 else ": " + year_list(years)}.')
    s2 = f'The smallest unit is the {unit}.' if unit_raw and ',' not in unit_raw else (
        f'The smallest unit is the {unit_raw.lower()}.' if unit_raw else '')
    pct = round(100 * top['share_located']) if top['share_located'] is not None else None
    s3 = (f'The {y1} election has {top["units"]:,} {plural(unit) if unit_raw and "," not in unit_raw else "units"}'
          + (f', and {pct}% of them have a location.' if pct else '.'))
    if len(poly_years) == len(years):
        s4 = 'Unit boundaries are available for every election.'
    elif poly_years:
        s4 = f'Unit boundaries are available for {year_list(poly_years)}.'
    else:
        s4 = 'There are no unit boundaries for this country.'
    summary = ' '.join(x for x in (s1, s2, s3, s4) if x)

    title_unit = unit if unit_raw else 'smallest unit'
    title = f'{c} election results by {title_unit}, {span_txt} | SAGE'
    desc = (f'{c} {" and ".join(type_words)} election results by {title_unit} for {year_list(years)}, '
            f'geocoded{" with boundaries" if poly_years else ""}. Free download as CSV, GeoPackage, Parquet or R.')

    # elections table
    trs = []
    prev = None
    for r in rows:
        first = r['year'] != prev
        explore = f'{EXPLORER}#c={E(c)}&amp;y={r["year"]}'
        map_link = '<a href="' + explore + '">[map]</a>'
        trs.append(
            f'<tr><td>{r["year"] if first else ""}</td><td>{E(r["election_type"] or "")}</td>'
            f'<td>{E(r["special_type"] or "")}</td><td class="num">{r["round"] or ""}</td>'
            f'<td class="num">{r["units"]:,}</td>'
            f'<td class="num">{"" if r["share_located"] is None else str(round(100 * r["share_located"])) + "%"}</td>'
            f'<td class="num">{"" if r["votes"] is None else format(r["votes"], ",")}</td>'
            f'<td>{"yes" if r["polygons"] else ""}</td>'
            f'<td>{map_link if first else ""}</td></tr>')
        prev = r['year']
    elections = '\n'.join(trs)

    # downloads
    d = downloads.get(c)
    if d:
        alls = ' '.join(x for x in (dl_cell(d['all'].get(k), k) for k in ('csv', 'gpkg', 'parquet', 'rds', 'codebook')) if x)
        yrs = '\n'.join(
            f'<tr><td>{y}</td><td>' + ' '.join(x for x in (dl_cell(d['years'][y].get(k), k) for k in ('csv', 'gpkg', 'parquet')) if x)
            + '</td></tr>' for y in sorted(d['years'], reverse=True))
        dl_html = (f'<p><strong>All years:</strong> {alls}</p>\n'
                   f'<div class="table-scroll"><table class="plain"><thead><tr><th>Year</th><th>Downloads</th></tr></thead>'
                   f'<tbody>\n{yrs}\n</tbody></table></div>')
    else:
        dl_html = f'<p>See the <a href="/#download">download section</a> on the main page.</p>'
    # results added up within administrative areas
    a = admin_dl.get(c) or {}
    if a:
        order = ['gadm1', 'gadm2', 'gadm3', 'gadm4', 'gadm5', 'nuts1', 'nuts2', 'nuts3', 'us_county']
        cells = ' '.join(dl_cell({'path': a[lv]['path'], 'bytes': a[lv]['bytes']},
                                 f'{a[lv]["label"].lower()} csv') for lv in order if lv in a)
        dl_html += (f'\n    <p><strong>By area:</strong> {cells}</p>\n'
                    f'    <p class="facts" style="font-size:0.9em;">The same results added up within administrative '
                    f'areas (GADM 4.1{", Eurostat NUTS" if any(k.startswith("nuts") for k in a) else ""}'
                    f'{", US counties" if "us_county" in a else ""}), all years in one file per level. You can also '
                    f'<a href="{EXPLORER}#c={E(c)}&amp;a={next(lv for lv in order if lv in a)}">map them</a>.</p>')

    sources = m.get('sources', [])
    notes = m.get('notes', [])
    src_html = ('<h2>Sources</h2>\n<ul>' + ''.join(f'<li>{E(s)}</li>' for s in sources) + '</ul>') if sources else ''
    notes_html = ('<h2>Notes</h2>\n<ul>' + ''.join(f'<li>{E(n)}</li>' for n in notes) + '</ul>') if notes else ''

    ld = {
        '@context': 'https://schema.org/', '@type': 'Dataset',
        'name': f'{c} election results by {title_unit}, {span_txt} (SAGE)',
        'description': desc + ' Part of the Small-Area Global Elections (SAGE) Dataset.',
        'url': f'{SITE}/{slug(c)}/',
        'keywords': ['elections', 'election results', 'polling stations', c, f'{c} elections', 'geocoded'],
        'license': 'https://creativecommons.org/licenses/by/4.0/', 'isAccessibleForFree': True,
        'creator': {'@type': 'Person', 'name': 'Noah Dasanaike'},
        'isPartOf': {'@type': 'Dataset', 'name': 'The Small-Area Global Elections (SAGE) Dataset', 'url': f'{SITE}/',
                     'identifier': DOI},
        'temporalCoverage': f'{y0}/{y1}',
        'spatialCoverage': {'@type': 'Place', 'name': c},
        'citation': 'Dasanaike, Noah. "The Small-Area Global Elections (SAGE) Dataset." Scientific Data (2026).',
    }
    if d:
        dist = []
        for k, fmt in (('csv', 'application/zip'), ('gpkg', 'application/zip'), ('parquet', 'application/zip')):
            f = d['all'].get(k)
            if f and f.get('path'):
                dist.append({'@type': 'DataDownload', 'encodingFormat': fmt, 'name': f'{k}, all years',
                             'contentUrl': gcs_url(f['path'])})
        ld['distribution'] = dist

    also_cite = ('<p>Some of these data come from other researchers&rsquo; collections; see '
                 '<a href="/#attribution">please also cite</a>.</p>') if c in ALSO_CITE else ''
    i = countries.index(c)
    prev_c, next_c = countries[i - 1], countries[(i + 1) % N]
    page = f"""<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{E(title)}</title>
    <meta name="description" content="{E(desc)}" />
    <link rel="canonical" href="{SITE}/{slug(c)}/" />
    <link rel="stylesheet" href="/style.css" />
    <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
    </script>
</head>

<body>
    <div class="crumbs"><a href="/">SAGE</a> &rsaquo; <a href="/#countries">Countries</a> &rsaquo; {E(c)}</div>

    <header>
        <h1>{E(c)}: election results by {E(title_unit)}</h1>
        <p class="facts">{span} &middot; {len(years)} election{"s" if len(years) != 1 else ""}
            {"&middot; " + E(iso3) if iso3 else ""}</p>
    </header>

    <p>{summary}</p>

    <p class="toplinks">
        [<a href="{EXPLORER}#c={E(c)}">explore on the map</a>]
        [<a href="#download">download</a>]
        [<a href="{gcs_url(d['all']['codebook']['path']) if d and d['all'].get('codebook') else GCS + '/codebook.pdf'}" target="_blank" rel="noopener">codebook</a>]
        [<a href="/">all {N} countries</a>]
    </p>

    <h2>Elections</h2>
    <p>Units are the smallest units in the data, and located units are those with coordinates.
        A year with several rows has several contests or votes; filter on them before you add up votes.</p>
    <div class="table-scroll">
        <table class="plain">
            <thead>
                <tr><th>Year</th><th>Election type</th><th>Vote type</th><th class="num">Round</th>
                    <th class="num">Units</th><th class="num">% located</th><th class="num">Votes</th>
                    <th>Polygons</th><th></th></tr>
            </thead>
            <tbody>
{elections}
            </tbody>
        </table>
    </div>

    <h2 id="download">Download</h2>
    <p><strong>csv</strong> opens in Excel, Stata, R, or Python. <strong>gpkg</strong> has the unit boundaries
        for QGIS, ArcGIS, R, or Python. <strong>parquet</strong> has the vote rows as Parquet.
        <strong>rds</strong> is the native R <code>sf</code> object. Each ZIP has a README with the columns.</p>
    {dl_html}

    <p>In R or Python:</p>
    <pre>R:      install.packages("sage")
        sage::sage_load("{E(c)}", years = {y1})

Python: import sage
        sage.sage_load("{E(c)}", years=[{y1}])</pre>

    {src_html}
    {notes_html}

    <h2>Citation</h2>
    <p>{CITE} <a href="{PAPER}">Paper</a> &middot; <a href="{DOI}">Harvard Dataverse</a></p>
    {also_cite}

    <p class="crumbs" style="margin-top:2em;">
        &larr; <a href="/{slug(prev_c)}/">{E(prev_c)}</a> &middot; <a href="/">All countries</a> &middot;
        <a href="/{slug(next_c)}/">{E(next_c)}</a> &rarr;
    </p>
</body>

</html>
"""
    wr(f'{slug(c)}/index.html', page)


for c in countries:
    country_page(c)

# ---------------------------------------------------------------- sitemap, robots, 404, CNAME
urls = [f'{SITE}/'] + [f'{SITE}/{slug(c)}/' for c in countries]
wr('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'
   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
   + ''.join(f'  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n' for u in urls) + '</urlset>\n')
wr('robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
wr('CNAME', 'sage-elections.com\n')
wr('.nojekyll', '')
wr('404.html', f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Page not found | SAGE</title><link rel="stylesheet" href="/style.css" /></head>
<body><h1>Page not found</h1><p><a href="/">Go to the SAGE home page</a>, which lists all {N} countries.</p></body></html>
""")
print(f'built index + {N} country pages; downloads for {len(downloads)} countries')
