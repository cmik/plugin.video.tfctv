#!/usr/bin/env python3
"""Publish a release zip in a checkout of the cmik.xbmc repository.

usage: update_repo.py <cmik.xbmc dir> <zip>

- copies the zip to downloads/<id>/<id>-<version>.zip and <id>-latest.zip
- replaces the <addon> entry of addons.xml with the addon.xml found in the zip
- rewrites addons.xml.md5 (the hash only, as Kodi expects)
"""
import hashlib
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

repo, zipPath = Path(sys.argv[1]), Path(sys.argv[2])

with zipfile.ZipFile(zipPath) as z:
    names = [n for n in z.namelist() if re.fullmatch(r'[^/]+/addon\.xml', n)]
    if len(names) != 1:
        sys.exit('ERROR: %s should contain exactly one <folder>/addon.xml' % zipPath)
    source = z.read(names[0]).decode('utf-8')

addon = ET.fromstring(source)
addonId, version = addon.get('id'), addon.get('version')
if zipPath.name != '%s-%s.zip' % (addonId, version):
    sys.exit('ERROR: %s should be named %s-%s.zip' % (zipPath.name, addonId, version))

target = repo / 'downloads' / addonId
target.mkdir(parents=True, exist_ok=True)
shutil.copyfile(zipPath, target / zipPath.name)
shutil.copyfile(zipPath, target / ('%s-latest.zip' % addonId))

entry = source[source.index('<addon '):].strip()
entry = '\n'.join(('    ' + line) if line.strip() else '' for line in entry.splitlines())

addonsFile = repo / 'addons.xml'
addons = addonsFile.read_text(encoding='utf-8')
pattern = re.compile(r'[ \t]*<addon id="%s".*?</addon>' % re.escape(addonId), re.S)
if not pattern.search(addons):
    sys.exit('ERROR: %s is not listed in addons.xml' % addonId)
addons = pattern.sub(lambda m: entry, addons, count=1)
addonsFile.write_text(addons, encoding='utf-8')

(repo / 'addons.xml.md5').write_text(hashlib.md5(addons.encode('utf-8')).hexdigest(), encoding='utf-8')
print('%s %s published in %s' % (addonId, version, repo))
