# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik

    Catalog seed: ready-made catalog databases (shows, episodes, celebrities) published as an
    asset of a GitHub release, so that a new installation or a major update doesn't have to load
    the whole catalog from the website. The seed contains no user data (see models/userdata.py).
'''

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from urllib import request as libRequest

try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from resources.lib.libraries import control
from resources.lib.models import userdata

logger = control.logger

FORMAT = 1
MANIFEST = 'manifest.json'
# databases of the seed: file name -> table that must exist and the key of the counts of the manifest
DATABASES = (('shows.db', 'SHOW', 'shows'), ('episodes.db', 'EPISODE', 'episodes'), ('celebrities.db', 'SHOW_CAST', 'celebrities'))
# first version whose catalog ids are the ones of the new website API
FIRST_CURRENT_MAJOR = 3
TIMEOUT = 30


def seedReason(lastVersion):
    """Why the catalog seed must be installed: 'install' (first installation), 'major' (update from
    a version whose catalog is not usable anymore) or None"""
    lastVersion = (lastVersion or '').strip()
    if lastVersion == '':
        return 'install'
    try:
        if int(lastVersion.split('.')[0]) < FIRST_CURRENT_MAJOR:
            return 'major'
    except ValueError:
        return 'major'
    return None


def _open(url):
    return libRequest.urlopen(libRequest.Request(url, headers={'User-Agent': 'plugin.video.tfctv'}), timeout=TIMEOUT)


def fetchManifest(baseUrl):
    """Read the manifest of the published seed (None when it can't be read or isn't usable)"""
    try:
        manifest = json.loads(_open(baseUrl + MANIFEST).read().decode('utf-8'))
    except Exception as e:
        logger.logError('Can\'t read the catalog seed manifest: %s' % str(e))
        return None
    if not isinstance(manifest, dict) or manifest.get('format') != FORMAT or not manifest.get('file') or not manifest.get('sha256'):
        logger.logError('Unusable catalog seed manifest')
        return None
    return manifest


def download(baseUrl, manifest, directory, progress=None):
    """Download the zip of the seed in `directory` and check its size and sha256. Returns its path."""
    path = os.path.join(directory, os.path.basename(manifest['file']))
    digest = hashlib.sha256()
    size = 0
    with _open(baseUrl + manifest['file']) as response, open(path, 'wb') as out:
        total = int(manifest.get('size') or response.headers.get('Content-Length') or 0)
        while True:
            chunk = response.read(256 * 1024)
            if not chunk:
                break
            out.write(chunk)
            digest.update(chunk)
            size += len(chunk)
            if progress and total:
                progress(min(100, 100 * size // total))
    if digest.hexdigest() != manifest['sha256'] or (manifest.get('size') and size != int(manifest['size'])):
        raise ValueError('The downloaded catalog seed is corrupted')
    return path


def extract(zipPath, directory, manifest):
    """Extract and check the databases of the seed. Returns {file name: path}."""
    files = {}
    with zipfile.ZipFile(zipPath) as archive:
        names = archive.namelist()
        for name, table, key in DATABASES:
            if name not in names:
                raise ValueError('%s is missing from the catalog seed' % name)
            path = os.path.join(directory, name)
            with archive.open(name) as src, open(path, 'wb') as out:
                shutil.copyfileobj(src, out)
            files[name] = path
            check(path, table, int((manifest.get('counts') or {}).get(key, 1)))
    return files


def check(path, table, minimum=1):
    """A usable database: not corrupted and its table has at least `minimum` rows"""
    db = database.connect(path)
    try:
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('%s is corrupted' % os.path.basename(path))
        count = db.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0]
        if count < minimum:
            raise ValueError('%s has %d rows instead of %d' % (os.path.basename(path), count, minimum))
    finally:
        db.close()


def install(files, targets):
    """Put the databases in place. The ones they replace are kept as `.bak` and put back when a
    file can't be installed. `files` and `targets` are {file name: path}."""
    backups = {}
    try:
        for name, source in files.items():
            target = targets[name]
            if os.path.exists(target):
                backups[name] = target + '.bak'
                shutil.copyfile(target, backups[name])
            os.replace(source, target)  # same folder: atomic
    except Exception:
        for name, backup in backups.items():
            try:
                shutil.copyfile(backup, targets[name])
            except Exception as e:
                logger.logError('Can\'t restore %s: %s' % (targets[name], str(e)))
        raise


def remapMyList(userDataFile, showsFile):
    """After the catalog was replaced: look for the shows of My List that are not in it under their
    title (another catalog uses other ids). Returns (nb remapped, titles not found)."""
    ud = userdata.UserData(userDataFile)
    db = database.connect(showsFile)
    try:
        byTitle = {}
        ids = set()
        for showId, title in db.execute('SELECT ID, TITLE FROM SHOW'):
            ids.add(showId)
            byTitle.setdefault(userdata.normalizeTitle(title), []).append(showId)
    finally:
        db.close()
    remapped = 0
    notFound = []
    for showId, title in ud.getMyList():
        if showId in ids:
            continue
        candidates = byTitle.get(userdata.normalizeTitle(title), [])
        if len(candidates) == 1 and ud.replaceMyListId(showId, candidates[0]):
            remapped += 1
        else:
            notFound.append(title or showId)
    return remapped, notFound


def installCatalogSeed(baseUrl, targets, userDataFile, progress=None):
    """Download and install the catalog seed.

    Returns None when the seed can't be installed (the current databases are left as they are),
    else (titles of the shows of My List that couldn't be found again in the new catalog, manifest)."""
    manifest = fetchManifest(baseUrl)
    if manifest is None:
        return None
    directory = tempfile.mkdtemp(prefix='tfctv-seed-', dir=os.path.dirname(targets['shows.db']))
    try:
        zipPath = download(baseUrl, manifest, directory, progress)
        files = extract(zipPath, directory, manifest)
        install(files, targets)
        remapped, notFound = remapMyList(userDataFile, targets['shows.db'])
        logger.logNotice('Catalog seed %s installed (My List: %d remapped, %d not found)' % (manifest.get('catalogVersion'), remapped, len(notFound)))
        return notFound, manifest
    except Exception as e:
        logger.logError('Can\'t install the catalog seed: %s' % str(e))
        return None
    finally:
        shutil.rmtree(directory, ignore_errors=True)
