#!/usr/bin/env python3
"""Consistency checks on the add-on files that are edited by hand at each release.

- addon.xml is valid XML and declares a version
- the version is the first entry of changelog.txt and is announced in <news>
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

with open('changelog.txt', encoding='utf-8') as f:
    first = next((line.strip() for line in f if line.strip()), '')
if first != version:
    fail('the first entry of changelog.txt is "%s" but addon.xml version is "%s"' % (first, version))

news = addon.findtext('.//news') or ''
if not news.strip().lstrip('v').startswith(version or '?'):
    fail('<news> in addon.xml should start with the version %s' % version)

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
