#!/usr/bin/python3

import glob, os
import kcore.html as H
from dataclasses import dataclass

@dataclass
class Item:
    title: str
    label: str
    url: str
    source: str
    def search_blob(self): return f'{self.title} {self.label} {self.url}'.lower()
    def __str__(self): return f'<a href="{self.url}">{self.title or self.label}</a>'
    def highlight(self, search):
        label = self.title or self.label
        return f'<a href="{self.url}">{label.lower().replace(search, f"<b>{search}</b>")}</a>'

def get_quoted_element(line, leadup):
    pos_leadup = line.find(leadup)
    if pos_leadup < 0: return None
    pos_q1 = line.find('"', pos_leadup)
    pos_q2 = line.find('"', pos_q1 + 1)
    return line[pos_q1+1 : pos_q2]

def get_url(line):
    candidate = get_quoted_element(line, 'goto')
    if candidate: return candidate
    candidate = get_quoted_element(line, 'trigger')
    if candidate: return 'https://home.point0.net/homesec/trigger/' + candidate
    candidate = get_quoted_element(line, 'control')
    if candidate: return 'https://home.point0.net/control/' + candidate
    candidate = get_quoted_element(line, 'iframe')
    if candidate: return candidate
    return None

def get_button_label(line):
    pos_leadup = line.find('<button')
    if pos_leadup < 0: return None
    pos_q1 = line.find('>', pos_leadup)
    pos_q2 = line.find('<', pos_q1 + 1)
    return line[pos_q1+1 : pos_q2]

def parse_line(line, source):
    return Item(get_quoted_element(line, 'title'),
                get_button_label(line),
                get_url(line),
                source.replace('.html', '').replace('/var/www/html/launchpad/index', '').replace('-', ''))


def main():
    print('Content-Type: text/html\n')
    print('<html><body>\n')

    qs = os.environ.get('QUERY_STRING')
    hits = []
    for filename in glob.glob('/var/www/html/launchpad/index*.html'):
        for line in open(filename):
            if not '<button class="bb" ' in line: continue
            item = parse_line(line, filename)
            if qs in item.search_blob(): hits.append(item)

    if len(hits) == 0:
        print('<p>not found.')

    elif len(hits) == 1:
        print(f'<meta http-equiv="refresh" content="0;URL={hits[0].url}">')

    else:
        hits2 = [[i.highlight(qs), i.source] for i in hits]
        print(H.list_to_table(hits2, table_fmt='border=0 cellpadding=2'))

    print('</body></html>\n')


if __name__ == '__main__':
    main()
