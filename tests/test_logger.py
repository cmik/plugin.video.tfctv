# -*- coding: utf-8 -*-
"""The Kodi log never holds a token, a cookie or a password"""

import importlib.util
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES = []
xbmc = types.ModuleType('xbmc')
xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 2, 3
xbmc.log = lambda text, level: LINES.append(text)
saved = sys.modules.get('xbmc')
sys.modules['xbmc'] = xbmc
try:
    spec = importlib.util.spec_from_file_location('logger_under_test', os.path.join(ROOT, 'resources', 'lib', 'libraries', 'logger.py'))
    logger = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logger)
finally:
    if saved is None:
        sys.modules.pop('xbmc', None)
    else:
        sys.modules['xbmc'] = saved

logger.getStack = lambda: [(None, 'test.py', 1, 'f')] * 4  # inspect.stack() chokes on the fake modules of the other tests

JWT = 'eyJ4NXQiOiIzNnRoYkh3RnVjQXdZ.eyJzdWIiOiJhYmMifQabcdefgh.SIGNATUREabcdef'


class RedactTest(unittest.TestCase):

    def test_secrets_are_hidden(self):
        for text, secret in (
            ('  Authorization: Bearer %s' % JWT, JWT),
            ("{'message': b'{\"token\":\"%s\"}'}" % JWT, JWT),
            ('Set-Cookie3: _abck="97EB53778407F4~-1~YAAQDY4"; path="/"; domain=x', '97EB53778407F4'),
            ('Cookie: bm_sz=92598C206808762 (domain=x, path=/)', '92598C206808762'),
            ("https://x/login - {'email': 'a@b.c', 'password': 'hunter2'}", 'hunter2'),
            ('access_token=abc123secret&code=1', 'abc123secret'),
            ('{"refresh_token":"r3fr3sh"}', 'r3fr3sh'),
        ):
            self.assertNotIn(secret, logger.redact(text), text)

    def test_the_rest_is_kept(self):
        for text in ('https://api.iwanttfc.com/watchlist/watchlist - {\'assetId\': \'27a40f60\'}', 'Authorization: Bearer ***', 'x-device-platform: web'):
            self.assertIn(text.split(' ')[0], logger.redact(text))
        self.assertEqual('Cookie: a=***', logger.redact('Cookie: a=b'))
        self.assertEqual('12', logger.redact(12))

    def test_the_log_line_is_redacted(self):
        logger.enable(True)
        logger.setLevel(logger.LOGDEBUG)
        del LINES[:]
        def caller():
            logger.logDebug('Authorization: Bearer %s' % JWT)
        caller()
        self.assertEqual(1, len(LINES))
        self.assertNotIn(JWT, LINES[0])
        self.assertIn('Bearer ***', LINES[0])


if __name__ == '__main__':
    unittest.main()
