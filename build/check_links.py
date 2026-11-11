"""HEAD every bucket link the site uses: hrefs in the built HTML and every path in the
download lists the main page loads at runtime. Run before pushing. Exit 1 on any failure."""
import glob, json, os, re, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
GCS = 'https://storage.googleapis.com/sage-archive/'
urls = set()
for f in glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True):
    if os.sep + 'deploy' + os.sep in f:
        continue
    for u in re.findall(r'href="(https://storage\.googleapis\.com/[^"#]+)"', open(f, encoding='utf-8').read()):
        urls.add(u.replace('&amp;', '&'))


def walk(o):
    if isinstance(o, dict):
        if isinstance(o.get('path'), str) and not o['path'].startswith('http'):
            urls.add(GCS + '/'.join(urllib.parse.quote(s) for s in o['path'].split('/')))
        for v in o.values():
            walk(v)


for name in ('sage_downloads.json', 'sage_admin_downloads.json'):
    p = os.path.join(ROOT, 'data', name)
    if os.path.exists(p):
        walk(json.load(open(p, encoding='utf-8')))


def head(u):
    try:
        urllib.request.urlopen(urllib.request.Request(u, method='HEAD'), timeout=30)
        return None
    except Exception as e:
        return (u, str(e))


with ThreadPoolExecutor(24) as ex:
    bad = [x for x in ex.map(head, sorted(urls)) if x]
print(len(urls), 'links checked;', len(bad), 'broken')
for b in bad[:30]:
    print(b)
sys.exit(1 if bad else 0)
