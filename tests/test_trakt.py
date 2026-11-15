# -*- coding: utf-8 -*-
"""Tests of the Trakt client: the scrobbled bodies, the device flow, the tokens and the scrobbling"""

import io
import json
import os
import sys
import unittest
from urllib.error import HTTPError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402  (fakes the Kodi control module)
import test_catalog_modules  # noqa: E402  (loads the catalog modules with Kodi faked)

from resources.lib.libraries import control, trakt  # noqa: E402

control.addonInfo = lambda key: '3.6.0' if key == 'version' else ''


class Store(object):
    def __init__(self):
        self.data = {}

    def getMeta(self, key, default=None):
        return self.data.get(key, default)

    def setMeta(self, key, value):
        self.data[key] = value


class Response(object):
    def __init__(self, status, body):
        self.status, self.raw = status, json.dumps(body).encode('utf-8') if body is not None else b''

    def getcode(self):
        return self.status

    def read(self):
        return self.raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Opener(object):
    """Answers the requests with the planned (status, body), in order, and keeps what was asked"""

    def __init__(self, *answers):
        self.answers, self.requests = list(answers), []

    def __call__(self, req, timeout=None):
        self.requests.append((req.full_url, json.loads(req.data) if req.data else None, dict(req.header_items())))
        status, body = self.answers.pop(0)
        if status >= 400:
            raise HTTPError(req.full_url, status, 'error', {}, io.BytesIO(json.dumps(body).encode('utf-8') if body is not None else b''))
        return Response(status, body)


TOKENS = {'access_token': 'A2', 'refresh_token': 'R2', 'expires_in': 7776000, 'created_at': 1000}


def client(*answers, **kwargs):
    store = kwargs.pop('store', None) or Store()
    opener = Opener(*answers)
    return trakt.Trakt(' id ', 'secret', store, opener, clock=lambda: 1000), store, opener


def connected(*answers, expires=1000 + 90 * 86400):
    store = Store()
    store.data.update({trakt.ACCESS: 'A1', trakt.REFRESH: 'R1', trakt.EXPIRES: expires})
    return client(*answers, store=store)


class BodyTest(unittest.TestCase):
    def test_episode_with_season_and_number(self):
        body = trakt.scrobbleBody({'title': 'S2 E10 - The end', 'ltype': 'show'}, {'name': 'Some Show'}, 12.345)
        self.assertEqual({'show': {'title': 'Some Show'}, 'episode': {'season': 2, 'number': 10}, 'progress': 12.35}, body)

    def test_show_name_of_the_episode_when_the_show_is_unknown(self):
        body = trakt.scrobbleBody({'title': 'S1 E1', 'ltype': 'show', 'show': 'From Episode'}, None, 0)
        self.assertEqual('From Episode', body['show']['title'])

    def test_movie_with_its_year(self):
        self.assertEqual({'movie': {'title': 'A Film', 'year': 2024}, 'progress': 0},
                         trakt.scrobbleBody({'title': 'A Film', 'ltype': 'movie', 'year': '2024'}, None, 0))

    def test_movie_without_year(self):
        self.assertEqual({'title': 'A Film'}, trakt.scrobbleBody({'title': 'A Film', 'ltype': 'movie', 'year': ''}, None, 0)['movie'])

    def test_what_can_not_be_told(self):
        self.assertIsNone(trakt.scrobbleBody(None, None, 0))
        self.assertIsNone(trakt.scrobbleBody({'title': 'Ep 24th Oct 2026 - Episode 1', 'ltype': 'show'}, {'name': 'Daily'}, 0))  # named by day
        self.assertIsNone(trakt.scrobbleBody({'title': 'S1 E1', 'ltype': 'show'}, {}, 0))  # no show title
        self.assertIsNone(trakt.scrobbleBody({'title': 'News', 'ltype': 'livestream'}, None, 0))

    def test_progress(self):
        self.assertEqual(50.0, trakt.progressOf(30, 60))
        self.assertEqual(100.0, trakt.progressOf(70, 60))
        self.assertEqual(0.0, trakt.progressOf(10, 0))
        self.assertEqual(0.0, trakt.progressOf(-5, 60))


def result(title, trakt_id, score=100):
    return {'type': 'show', 'score': score, 'show': {'title': title, 'year': 2023, 'ids': {'trakt': trakt_id}}}


class ShowSearchTest(unittest.TestCase):
    def test_titles_that_match(self):
        self.assertTrue(trakt.matches("FPJ's Batang Quiapo", 'Batang Quiapo'))
        self.assertTrue(trakt.matches('Batang Quiapo', "FPJ's Batang Quiapo"))
        self.assertTrue(trakt.matches('The Show!', 'the show'))
        self.assertFalse(trakt.matches('Batang Quiapo', 'Batang Hamog'))
        self.assertFalse(trakt.matches('', 'Anything'))
        self.assertFalse(trakt.matches('It', 'It Follows'))  # too short to be contained

    def test_best_title_among_the_results(self):
        c, _, opener = client((200, [result('Batang Quiapo: Behind the Scenes', 5, 900), result('Batang Quiapo', 202504, 400)]))
        self.assertEqual(202504, c.findShow("FPJ's Batang Quiapo"))  # the exact one before the better score
        self.assertIn('/search/show?query=FPJ%27s%20Batang%20Quiapo', opener.requests[0][0])
        self.assertNotIn('Authorization', opener.requests[0][2])

    def test_nothing_matches(self):
        self.assertIsNone(client((200, [result('Something Else', 1)]))[0].findShow('Batang Quiapo'))
        self.assertIsNone(client((200, []))[0].findShow('Batang Quiapo'))
        self.assertIsNone(client((500, None))[0].findShow('Batang Quiapo'))

    def test_the_id_is_remembered(self):
        c, store, opener = client((200, [result('Batang Quiapo', 202504)]))
        self.assertEqual(202504, c.resolveShow('s1', "FPJ's Batang Quiapo"))
        self.assertEqual(202504, c.resolveShow('s1', "FPJ's Batang Quiapo"))
        self.assertEqual(1, len(opener.requests))  # the second one comes from META

    def test_an_unknown_show_is_looked_for_again_after_a_day(self):
        now = [1000]
        opener = Opener((200, []), (200, [result('Batang Quiapo', 7)]))
        c = trakt.Trakt('id', '', Store(), opener, clock=lambda: now[0])
        self.assertIsNone(c.resolveShow('s1', 'Batang Quiapo'))
        self.assertIsNone(c.resolveShow('s1', 'Batang Quiapo'))
        self.assertEqual(1, len(opener.requests))
        now[0] += 86401
        self.assertEqual(7, c.resolveShow('s1', 'Batang Quiapo'))

    def test_an_unreachable_trakt_is_not_remembered_as_unknown(self):
        c, store, _ = client((0 + 500, None))
        self.assertIsNone(c.resolveShow('s1', 'Batang Quiapo'))
        self.assertIsNone(store.getMeta('traktShow:s1'))

    def test_the_body_uses_the_id_when_known(self):
        body = trakt.scrobbleBody({'title': 'S2 E194 - Bitag sa Bitag', 'ltype': 'show'}, {'name': "FPJ's Batang Quiapo"}, 0, 202504)
        self.assertEqual({'show': {'ids': {'trakt': 202504}}, 'episode': {'season': 2, 'number': 194}, 'progress': 0}, body)


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.settings = {}
        control.getAddonSetting = lambda key: self.settings.get(key, '')

    def test_the_application_of_the_add_on_by_default(self):
        c = trakt.fromSettings(Store())
        self.assertEqual(trakt.config.TRAKT_CLIENT_ID, c.clientId)
        self.assertEqual('', c.clientSecret)
        self.assertTrue(c.hasCredentials())

    def test_own_application(self):
        self.settings.update({'traktClientId': ' mine ', 'traktClientSecret': 'its-secret'})
        c = trakt.fromSettings(Store())
        self.assertEqual(('mine', 'its-secret'), (c.clientId, c.clientSecret))

    def test_the_secret_alone_is_not_used_with_the_application_of_the_add_on(self):
        self.settings['traktClientSecret'] = 'orphan'
        self.assertEqual('', trakt.fromSettings(Store()).clientSecret)


class DeviceFlowTest(unittest.TestCase):
    def test_device_code(self):
        c, _, opener = client((200, {'device_code': 'D', 'user_code': 'U', 'verification_url': 'https://trakt.tv/activate', 'expires_in': 600, 'interval': 5}))
        self.assertEqual('U', c.deviceCode()['user_code'])
        url, body, headers = opener.requests[0]
        self.assertEqual('https://api.trakt.tv/oauth/device/code', url)
        self.assertEqual({'client_id': 'id'}, body)  # trimmed
        self.assertEqual('id', headers['Trakt-api-key'])
        self.assertNotIn('Python', headers.get('User-agent', ''))
        self.assertTrue(headers['User-agent'].startswith('plugin.video.tfctv/'))

    def test_device_code_refused(self):
        self.assertIsNone(client((403, None))[0].deviceCode())
        self.assertIsNone(client((500, None))[0].deviceCode())

    def test_polling_until_entered(self):
        c, store, _ = client((400, None), (429, None), (200, TOKENS))
        self.assertEqual('pending', c.pollToken('D'))
        self.assertEqual('slow', c.pollToken('D'))
        self.assertFalse(c.isConnected())
        self.assertEqual('connected', c.pollToken('D'))
        self.assertTrue(c.isConnected())
        self.assertEqual('A2', store.data[trakt.ACCESS])
        self.assertEqual(1000 + 7776000, store.data[trakt.EXPIRES])

    def test_polling_failures(self):
        for status in (404, 409, 410, 418):
            self.assertEqual('failed', client((status, None))[0].pollToken('D'))

    def test_credentials(self):
        self.assertTrue(client()[0].hasCredentials())
        self.assertFalse(trakt.Trakt('', 'secret', Store()).hasCredentials())
        self.assertTrue(trakt.Trakt('id', '', Store()).hasCredentials())  # a public client has no secret

    def test_the_secret_is_sent_only_when_there_is_one(self):
        withSecret, _, opener = client((400, None))
        withSecret.pollToken('D')
        self.assertEqual({'code': 'D', 'client_id': 'id', 'client_secret': 'secret'}, opener.requests[0][1])
        opener = Opener((400, None))
        trakt.Trakt('id', '', Store(), opener).pollToken('D')
        self.assertEqual({'code': 'D', 'client_id': 'id'}, opener.requests[0][1])


class ScrobbleTest(unittest.TestCase):
    BODY = {'movie': {'title': 'X'}, 'progress': 10}

    def test_not_connected(self):
        c, _, opener = client()
        self.assertEqual(0, c.scrobble('start', self.BODY))
        self.assertEqual([], opener.requests)

    def test_scrobble_with_the_token(self):
        c, _, opener = connected((201, {'action': 'start'}))
        self.assertEqual(201, c.scrobble('start', self.BODY))
        url, body, headers = opener.requests[0]
        self.assertEqual('https://api.trakt.tv/scrobble/start', url)
        self.assertEqual(self.BODY, body)
        self.assertEqual('Bearer A1', headers['Authorization'])

    def test_token_close_to_expiry_is_refreshed_first(self):
        c, store, opener = connected((200, TOKENS), (201, None), expires=1000 + 60)
        self.assertEqual(201, c.scrobble('pause', self.BODY))
        self.assertEqual('https://api.trakt.tv/oauth/token', opener.requests[0][0])
        self.assertEqual('refresh_token', opener.requests[0][1]['grant_type'])
        self.assertEqual('Bearer A2', opener.requests[1][2]['Authorization'])
        self.assertEqual('R2', store.data[trakt.REFRESH])

    def test_rejected_token_is_refreshed_once_then_retried(self):
        c, _, opener = connected((401, None), (200, TOKENS), (201, None))
        self.assertEqual(201, c.scrobble('stop', self.BODY))
        self.assertEqual(['/scrobble/stop', '/oauth/token', '/scrobble/stop'], [r[0][len('https://api.trakt.tv'):] for r in opener.requests])

    def test_unreachable(self):
        c, _, opener = connected()
        opener.answers = []

        def down(req, timeout=None):
            raise OSError('no network')
        c.opener = down
        self.assertEqual(0, c.scrobble('start', self.BODY))

    def test_disconnect_forgets_the_tokens(self):
        c, store, opener = connected((200, None))
        c.disconnect()
        self.assertEqual('https://api.trakt.tv/oauth/revoke', opener.requests[0][0])
        self.assertFalse(c.isConnected())


if __name__ == '__main__':
    unittest.main()
