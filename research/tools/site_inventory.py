"""Inventory the organizer's linked pages, not the entire external web. Stdlib only."""
import csv
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
from urllib.parse import urljoin, urlsplit, urldefrag

BASE = 'https://www.hutter1.net/prize/'
OUT = Path(__file__).resolve().parents[1] / 'site'

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.text = []; self.hidden = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style'): self.hidden += 1
        if tag == 'sup': self.text.append('^')
        if tag in ('p', 'br', 'tr', 'li', 'div', 'h1', 'h2', 'h3', 'dt', 'dd'): self.text.append('\n')
        for attr in ('href', 'src'):
            if a.get(attr): self.links.append((tag, a[attr]))
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden -= 1
        if tag in ('td','th'): self.text.append(' | ')
    def handle_data(self, data):
        if not self.hidden: self.text.append(re.sub(r'\s+', ' ', data))

def local(u):
    p = urlsplit(u)
    if p.netloc == 'prize.hutter1.net': return BASE + p.path.lstrip('/')
    if p.netloc in ('www.hutter1.net','hutter1.net') and p.path.startswith('/prize/'): return BASE + p.path[7:]

def main():
    OUT.mkdir(exist_ok=True); queue = [BASE]; seen = set(); rows = []; pages = []
    while queue:
        u = queue.pop(0)
        if u in seen: continue
        seen.add(u); name = u[len(BASE):] or 'index.htm'
        r = subprocess.run(['curl','-fsSL','--max-time','30',u],capture_output=True)
        if r.returncode: pages.append((u,'failed','','')); continue
        raw = r.stdout; p = Page(); p.feed(raw.decode('utf8', 'replace'))
        pages.append((u,'retrieved',len(raw),hashlib.sha256(raw).hexdigest()))
        if name.endswith(('.htm','.html','.txt')):
            (OUT / (name.replace('/','_')+'.txt')).write_text('\n'.join(s.strip() for s in ''.join(p.text).splitlines() if s.strip()) if not name.endswith('.txt') else raw.decode('latin1'))
        for tag,href in p.links:
            dest = urljoin(u,href); item = local(urldefrag(dest)[0]); rows.append((u,tag,href,dest))
            if item and (item == BASE or item.endswith(('.htm','.html','.txt'))) and item not in seen: queue.append(item)
    for file,header,data in [('links.tsv',('from','tag','as_written','resolved'),rows),('pages.tsv',('url','status','bytes','sha256'),pages)]:
        with (OUT/file).open('w') as f:
            w=csv.writer(f,delimiter='\t'); w.writerow(header); w.writerows(data)
    print(len(pages),'page targets;',len(rows),'link occurrences')

if __name__ == '__main__': main()
