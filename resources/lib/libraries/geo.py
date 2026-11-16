# -*- coding: utf-8 -*-
'''
    Tfc.tv Add-on
    Country of the user: the catalog and the live channels depend on it (header x-country-code).
    Pure helpers, the calls are in sources/tfctv/user.py.
'''

import json
import re

SETTING = 'geoLocation'          # what the geo location service answered (JSON, kept between two starts)
OVERRIDE = 'countryOverride'     # country typed by the user in the settings (wins over the detected one)
AUTO = 'geoAutoUpdate'           # detect the country again at each start of the add-on


def normalize(code):
    """'fr ' -> 'FR'; '' when it is not a country code of two letters"""
    code = (code or '').strip().upper()
    return code if re.match(r'^[A-Z]{2}$', code) else ''


def stored(raw):
    """The geo location kept in the settings ({} when there is none or it can't be read)"""
    try:
        data = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def countryOf(location):
    """The country code of a geo location answer"""
    info = (location or {}).get('geoLocation', {})
    return normalize(info.get('countryCode', '') if isinstance(info, dict) else '')


def effectiveCountry(override, location):
    """The country used for the requests: the one of the user when it is valid, else the detected one"""
    return normalize(override) or countryOf(location)


def changed(old, new):
    """True when the detected country is not the one kept (a first detection counts as a change)"""
    return countryOf(new) != countryOf(old)
