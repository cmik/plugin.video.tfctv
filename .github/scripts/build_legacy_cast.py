#!/usr/bin/env python3
"""Build resources/data/legacy_cast.json: the show/actor links of the old catalog (before the
iWantTFC redesign) that can be attached to a show of the current catalog.

    python3 .github/scripts/build_legacy_cast.py <old celebrities.db> <old shows.db> <current shows.db> [output]

The old databases identify shows by slugs (`onthejob`); a show of the current catalog is found by
its title (normalized: case, accents and punctuation ignored) compared with the slug and with the
title the old shows.db has for it. Ambiguous matches are skipped, as are the shows that are not in
the current catalog anymore.
"""

import json
import os
import re
import sqlite3
import sys
import unicodedata


def normalize(title):
    title = unicodedata.normalize('NFKD', u'%s' % (title or ''))
    title = ''.join(c for c in title if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '', title.lower())


def main(argv):
    if len(argv) not in (4, 5):
        sys.exit(__doc__)
    oldCast, oldShows, currentShows = argv[1:4]
    output = argv[4] if len(argv) == 5 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'resources', 'data', 'legacy_cast.json')

    current = {}
    for showId, title in sqlite3.connect(currentShows).execute('SELECT ID, TITLE FROM SHOW'):
        current.setdefault(normalize(title), []).append(showId)
    oldTitles = dict(sqlite3.connect(oldShows).execute('SELECT ID, TITLE FROM SHOW').fetchall())

    def find(slug):
        for key in (normalize(slug), normalize(oldTitles.get(slug))):
            if key in current:
                return current[key][0] if len(current[key]) == 1 else None
        return None

    links = {}
    skipped = set()
    for slug, name, order in sqlite3.connect(oldCast).execute('SELECT SHOWID, NAME, ORDR FROM SHOW_CAST ORDER BY SHOWID, ORDR, NAME'):
        if not normalize(name):
            continue
        showId = find(slug)
        if showId is None:
            skipped.add(slug)
            continue
        names = links.setdefault(showId, {})
        names.setdefault(normalize(name), [name.strip(), int(order or 0)])

    result = {'format': 1, 'shows': dict((s, sorted(n.values(), key=lambda x: (x[1], x[0]))) for s, n in sorted(links.items()))}
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
        f.write('\n')
    print('%d shows, %d links, %d actors (%d old shows not in the current catalog) -> %s' % (
        len(links), sum(len(n) for n in links.values()), len(set(k for n in links.values() for k in n)), len(skipped), output))


if __name__ == '__main__':
    main(sys.argv)
