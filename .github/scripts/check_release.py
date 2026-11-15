#!/usr/bin/env python3
"""Consistency checks on the add-on files that are edited by hand at each release.

- addon.xml is valid XML and declares a version
- the version (without its development suffix) is the first entry of changelog.txt and is announced in <news>
- addon.xml.md5 is the md5 of addon.xml (only the hash, optionally followed by a newline)
- no Python bytecode is tracked by git
"""
import hashlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

errors = []


def fail(message):
    errors.append(message)
    print('ERROR: %s' % message)


try:
    addon = ET.parse('addon.xml').getroot()
except Exception as e:
    print('ERROR: addon.xml is not valid XML (%s)' % e)
    sys.exit(1)

version = addon.get('version')
if not version:
    fail('addon.xml has no version')
# between two releases the version carries a development suffix (3.6.0~dev1): Kodi sorts "~" before
# the same version without it, so 3.5.0 < 3.6.0~dev1 < 3.6.0. Only the version without suffix is released.
if version and not re.fullmatch(r'\d+\.\d+\.\d+(~[A-Za-z0-9.+_@]+)?', version):
    fail('the version "%s" should look like 3.6.0 or 3.6.0~dev1' % version)
base = (version or '').split('~')[0]
if version and '~' in version:
    print('NOTE: %s is a development version: it can not be released (the tag would not match)' % version)

with open('changelog.txt', encoding='utf-8') as f:
    first = next((line.strip() for line in f if line.strip()), '')
if first != base:
    fail('the first entry of changelog.txt is "%s" but the version of addon.xml is "%s"' % (first, version))

news = addon.findtext('.//news') or ''
if not news.strip().lstrip('v').startswith(base or '?'):
    fail('<news> in addon.xml should start with the version %s' % base)

with open('addon.xml', 'rb') as f:
    expected = hashlib.md5(f.read()).hexdigest()
with open('addon.xml.md5', encoding='utf-8') as f:
    actual = f.read()
if actual.rstrip('\n') != expected or not re.fullmatch(r'[0-9a-f]{32}\n?', actual):
    fail('addon.xml.md5 does not contain the md5 of addon.xml (expected %s); regenerate it with: '
         'md5 -q addon.xml | tr -d "\\n" > addon.xml.md5' % expected)

tracked = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=True).stdout.splitlines()
bytecode = [p for p in tracked if p.endswith('.pyc') or '/__pycache__/' in p or p.startswith('__pycache__/')]
if bytecode:
    fail('Python bytecode is tracked by git: %s' % ', '.join(bytecode[:5]))

if errors:
    sys.exit(1)
print('OK: version %s, changelog, news, md5 and tracked files are consistent' % version)
