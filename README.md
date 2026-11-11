# sage-elections.com

Website for the Small-Area Global Elections (SAGE) Dataset: the main page and one page per country.
The data and the R and Python packages are at <https://github.com/noahdasanaike/sage>.

## Building

The pages are generated. Edit `src/home.html` (main page) or `build/build_site.py` (country pages,
sitemap), never the generated `index.html` or `<country>/index.html`.

```
python build/collect_meta.py   # refresh src/country_meta.json from the README coverage table and codebook sheets
python build/build_site.py     # write index.html, style.css, <country>/index.html, sitemap.xml, robots.txt
```

Inputs in `data/`: `sage_coverage.json` / `.csv` (one row per contest) and `sage_downloads.json`
(download paths and sizes). Both are produced by the scripts in `J:/sage_v2_work/access_2026_11/scripts/`
and must be refreshed after every data release.
