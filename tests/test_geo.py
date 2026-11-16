# -*- coding: utf-8 -*-
"""Tests of the country used for the catalog and the live channels"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402,F401  (fakes the Kodi control module)

from resources.lib.libraries import geo  # noqa: E402

FR = {'ipAddress': '1.2.3.4', 'geoLocation': {'countryCode': 'FR'}}
PH = {'ipAddress': '5.6.7.8', 'geoLocation': {'countryCode': 'PH'}}


class GeoTest(unittest.TestCase):

    def test_normalize(self):
        self.assertEqual('FR', geo.normalize(' fr '))
        for bad in ('', None, 'F', 'FRA', 'F1', 'fr-FR'):
            self.assertEqual('', geo.normalize(bad))

    def test_the_stored_location_is_read_safely(self):
        self.assertEqual(FR, geo.stored(json.dumps(FR)))
        for raw in ('', None, 'not json', '[1]', '"x"'):
            self.assertEqual({}, geo.stored(raw))

    def test_country_of_a_location(self):
        self.assertEqual('FR', geo.countryOf(FR))
        for location in ({}, None, {'geoLocation': None}, {'geoLocation': {}}, {'geoLocation': {'countryCode': 'xx1'}}):
            self.assertEqual('', geo.countryOf(location))

    def test_the_country_of_the_user_wins(self):
        self.assertEqual('PH', geo.effectiveCountry('ph', FR))
        self.assertEqual('FR', geo.effectiveCountry('', FR))
        self.assertEqual('FR', geo.effectiveCountry('france', FR))  # not a code: ignored
        self.assertEqual('', geo.effectiveCountry('', {}))

    def test_a_new_country_replaces_the_old_one(self):
        self.assertTrue(geo.changed(FR, PH))
        self.assertTrue(geo.changed({}, FR))
        self.assertFalse(geo.changed(FR, dict(FR, ipAddress='9.9.9.9')))


if __name__ == '__main__':
    unittest.main()
