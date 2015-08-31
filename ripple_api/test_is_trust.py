# -*- coding: utf-8 -*-
import json

from django.conf import settings
from django.test import TestCase

from requests import Response

from mock import patch

import ripple_api

data = {
    u'status': u'success',
    u'lines': [
        {
            u'account': u'rhhPzptf4EdiRRopSVC3AEbHwDa9df8y2i',
            u'quality_out': 0,
            u'quality_in': 0,
            u'currency': u'USD',
            u'limit_peer': u'5',
            u'limit': u'2.5',
            u'balance': u'1.759565201742073',
        }, {
            u'account': u'rhhPzptf4EdiRRopSVC3AEbHwDa9df8y2i',
            u'quality_out': 0,
            u'no_ripple_peer': True,
            u'quality_in': 0,
            u'currency': u'CCK',
            u'limit_peer': u'2',
            u'limit': u'0',
            u'balance': u'0',
        }, {
            u'account': u'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7',
            u'quality_out': 0,
            u'quality_in': 0,
            u'currency': u'CCK',
            u'limit_peer': u'0',
            u'limit': u'1000000',
            u'balance': u'7.51418646934461',
        }, {
            u'account': u'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7',
            u'quality_out': 0,
            u'quality_in': 0,
            u'currency': u'USD',
            u'limit_peer': u'0',
            u'limit': u'10000',
            u'balance': u'0.7907',
        }],
    u'account': u'rJmEYVEB7Bw16Kt9FYHK74Xrgery6gN6AB',
    u'validated': False,
    u'ledger_current_index': 12159817,
}

untrusted_data = {
    "account": "rJmEYVEB7Bw16Kt9FYHK74Xrgery6gN6AB",
    "lines": [],
    "status": "success"
}


class IsTrustSetTestCase(TestCase):

    def setUp(self):
        self.servers = settings.RIPPLE_API_DATA
        self.account = u'rJmEYVEB7Bw16Kt9FYHK74Xrgery6gN6AB'
        self.trusted_peer = u"rhhPzptf4EdiRRopSVC3AEbHwDa9df8y2i"
        self.untrusted_peer = u"rJobmmpNqozqY7MzwGkRs1VLEBJ7H5Pjrp"
        self.usd_granted_limit = 1
        self.usd_overgranted_limit = 10

    @patch('requests.post')
    def test_detect_trusted_peer(self, post_mock):
        """ Test if is_trust_set detects trusted peer
        """
        response = Response()
        response._content = json.dumps({u"result": data})
        post_mock.return_value = response

        is_trusted = ripple_api.is_trust_set(self.account,
                                             self.trusted_peer,
                                             currency="USD",
                                             servers=self.servers)

        self.assertEqual(is_trusted, True)

    @patch('requests.post')
    def test_detect_untrusted_peer(self, post_mock):
        """ Test if is_trust_set detects untrusted peer
        """
        response = Response()
        response._content = json.dumps({u"result": untrusted_data})
        post_mock.return_value = response

        is_trusted = ripple_api.is_trust_set(self.account,
                                             self.untrusted_peer,
                                             currency="USD",
                                             servers=self.servers)

        self.assertEqual(is_trusted, False)

    @patch('requests.post')
    def test_detect_trusted_in_general_not_trusted_in_eur(self, post_mock):
        """ Test if is_trust_set detects trusted in general peer
            but not trusted in certain currency (EUR)
        """
        response = Response()
        response._content = json.dumps({u"result": data})
        post_mock.return_value = response

        is_trusted_in_general = ripple_api.is_trust_set(self.account,
                                                        self.trusted_peer,
                                                        servers=self.servers)

        self.assertEqual(is_trusted_in_general, True)
        is_trusted_eur = ripple_api.is_trust_set(self.account,
                                                 self.trusted_peer,
                                                 currency="EUR",
                                                 servers=self.servers)

        self.assertEqual(is_trusted_eur, False)

    @patch('requests.post')
    def test_detect_limit_enough(self, post_mock):
        """ Test if is_trust_set detects if limit is enough
        """
        response = Response()
        response._content = json.dumps({u"result": data})
        post_mock.return_value = response

        is_trusted = ripple_api.is_trust_set(self.account,
                                             self.untrusted_peer,
                                             currency="USD",
                                             limit=self.usd_granted_limit,
                                             servers=self.servers)

        self.assertEqual(is_trusted, True)

    @patch('requests.post')
    def test_detect_limit_not_enough(self, post_mock):
        """ Test if is_trust_set detects if limit is not enough
        """
        response = Response()
        response._content = json.dumps({u"result": data})
        post_mock.return_value = response

        is_trusted = ripple_api.is_trust_set(self.account,
                                             self.untrusted_peer,
                                             currency="USD",
                                             limit=self.usd_overgranted_limit,
                                             servers=self.servers)

        self.assertEqual(is_trusted, False)
