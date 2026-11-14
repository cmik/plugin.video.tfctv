#!/usr/bin/env python3
"""Build the catalog seed from the databases of a Kodi profile.

    python3 .github/scripts/build_seed.py <addon_data folder> <output folder> [--catalog-version 2026-11-14]

The addon_data folder is the one of the add-on in the Kodi profile (it holds shows.db,
episodes.db and celebrities.db, filled with "Reload Catalog Cache"). The output folder gets
catalog-seed.zip and manifest.json: publish them as the assets of the GitHub release
`catalog-seed` (see CLAUDE.md). Whatever belongs to the user (My List, views, ratings, votes)
is cleared in the copies; the source databases are not modified.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import zipfile

FORMAT = 1
ZIP_NAME = 'catalog-seed.zip'
# file -> (table, manifest count key, minimum rows of a usable database, columns to reset)
DATABASES = {
    'shows.db': ('SHOW', 'shows', 100, "VIEWS = 0, RATING = 0, VOTES = 0, MYLIST = 'false'"),
    'episodes.db': ('EPISODE', 'episodes', 1000, 'VIEWS = 0, RATING = 0, VOTES = 0'),
    'celebrities.db': ('SHOW_CAST', 'celebrities', 1, None),
}


def addonVersion(root):
    with open(os.path.join(root, 'addon.xml'), encoding='utf-8') as f:
        return re.search(r'<addon[^>]*\sversion="([^"]+)"', f.read()).group(1)


def sanitize(source, target, table, reset):
    shutil.copyfile(source, target)
    db = sqlite3.connect(target)
    try:
        if reset:
            db.execute('UPDATE %s SET %s' % (table, reset))
            db.commit()
        db.execute('VACUUM')
        return db.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0]
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source')
    parser.add_argument('output')
    parser.add_argument('--catalog-version', default=datetime.date.today().isoformat())
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.makedirs(args.output, exist_ok=True)
    counts = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (table, key, minimum, reset) in DATABASES.items():
            source = os.path.join(args.source, name)
            if not os.path.exists(source):
                sys.exit('%s not found in %s' % (name, args.source))
            counts[key] = sanitize(source, os.path.join(tmp, name), table, reset)
            if counts[key] < minimum:
                sys.exit('%s has only %d rows (at least %d expected): load the catalog first' % (name, counts[key], minimum))
        zipPath = os.path.join(args.output, ZIP_NAME)
        with zipfile.ZipFile(zipPath, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in DATABASES:
                archive.write(os.path.join(tmp, name), name)

    with open(zipPath, 'rb') as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    manifest = {
        'format': FORMAT,
        'catalogVersion': args.catalog_version,
        'addonVersion': addonVersion(root),
        'file': ZIP_NAME,
        'size': os.path.getsize(zipPath),
        'sha256': sha256,
        'counts': counts,
    }
    with open(os.path.join(args.output, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
        f.write('\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
