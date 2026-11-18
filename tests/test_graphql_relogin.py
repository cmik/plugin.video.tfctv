# -*- coding: utf-8 -*-
"""An expired token on GraphQL (an error inside a 200) is renewed once by callGraphQLApi"""

import importlib
import json
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402

PACKAGE = 'resources.lib.sources.tfctv'
control = test_userdata.control
control.pathExists = getattr(control, 'pathExists', lambda p: False)
control.tempPath = getattr(control, 'tempPath', '/tmp')
control.dataPath = getattr(control, 'dataPath', '/tmp')
control.readFile = getattr(control, 'readFile', lambda p: '')
control.showNotification = lambda *a, **k: None
control.lang = lambda n: ''
control.setting = lambda key: 'TOKEN' if key == 'iWantUserAuthentication' else ''

package = types.ModuleType(PACKAGE)
package.__path__ = [os.path.join(test_userdata.ROOT, 'resources', 'lib', 'sources', 'tfctv')]
user = types.ModuleType(PACKAGE + '.user')
user.getCountryCode = lambda: 'PH'
auth = types.ModuleType(PACKAGE + '.auth')
saved = dict((k, sys.modules.get(k)) for k in (PACKAGE, PACKAGE + '.user', PACKAGE + '.auth'))
sys.modules.update({PACKAGE: package, PACKAGE + '.user': user, PACKAGE + '.auth': auth})
try:
    api = importlib.import_module(PACKAGE + '.api')
finally:
    for key, module in saved.items():
        if module is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = module

ERROR = json.dumps({'errors': [{'message': 'Failed to get watchlist'}], 'data': None})
GOOD = json.dumps({'data': {'watchlist': {'items': []}}})
BEARER = ('Authorization', 'Bearer old')


class RenewTest(unittest.TestCase):

    def setUp(self):
        keys = (PACKAGE, PACKAGE + '.user', PACKAGE + '.auth')
        self.saved = dict((k, sys.modules.get(k)) for k in keys)
        sys.modules.update({PACKAGE: package, PACKAGE + '.user': user, PACKAGE + '.auth': auth})  # the lazy imports
        self.addCleanup(self.restore)
        self.sent = []
        self.answers = [ERROR, GOOD]
        self.logins = []
        self.token = 'TOKEN'
        auth.login = lambda quiet=False: self.logins.append(1) or True
        control.setting = lambda key: self.token
        api.callServiceApi = self.fake
        api._lastRelogin = 0

    def restore(self):
        for key, module in self.saved.items():
            if module is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = module

    def fake(self, path, params, headers, *a, **k):
        self.sent.append(dict(headers).get('Authorization'))
        return self.answers.pop(0)

    def test_error_then_login_then_answer(self):
        self.assertEqual({'watchlist': {'items': []}}, api.callGraphQLApi('q', headers=[BEARER]))
        self.assertEqual(1, len(self.logins))
        self.assertEqual(['Bearer old', 'Bearer TOKEN'], self.sent)

    def test_asked_only_twice_and_login_not_repeated(self):
        self.answers = [ERROR, ERROR, ERROR, ERROR]
        self.assertEqual({}, api.callGraphQLApi('q', headers=[BEARER]))
        self.assertEqual(2, len(self.sent))
        self.assertEqual({}, api.callGraphQLApi('q', headers=[BEARER]))  # logged in a minute ago: no new login
        self.assertEqual(1, len(self.logins))
        self.assertEqual(3, len(self.sent))

    def test_no_login_without_a_token(self):
        self.answers = [ERROR]
        self.assertEqual({}, api.callGraphQLApi('q'))
        self.assertEqual([], self.logins)

    def test_failed_login_gives_up(self):
        self.answers = [ERROR]
        auth.login = lambda quiet=False: False
        self.assertEqual({}, api.callGraphQLApi('q', headers=[BEARER]))
        self.assertEqual(1, len(self.sent))


if __name__ == '__main__':
    unittest.main()
