# -*- coding: utf-8 -*-
import json

from django.conf import settings
from django.test import TestCase

from requests import Response

from mock import patch
from decimal import Decimal

import ripple_api

sequence = 12
destination_account = u'rJobmmpNqozqY7MzwGkRs1VLEBJ7H5Pjrp'
wrong_secret = "somesecret"

responses = {
    "account_lines": {
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
    },
    "account_info": {
        u'status': u'success',
        u'validated': True,
        u'account_data': {
            u'OwnerCount': 3,
            u'index': u'BD2C319063E47D3546796E19DE5716B14107514C4AF61C5FE0C528637D17DA20',
            u'Account': u'rJmEYVEB7Bw16Kt9FYHK74Xrgery6gN6AB',
            u'PreviousTxnID': u'847AA9D8B49955D1216BAA9D3262AFC3DAB5CCB9FD9ED12A0F5FA65B874D4E2B',
            u'Sequence': 44,
            u'LedgerEntryType': u'AccountRoot',
            u'Flags': 0,
            u'PreviousTxnLgrSeq': 12153785,
            u'Balance': u'50488267',
            },
        u'ledger_index': 12159865,
    }
}


def side_effect(data, servers=None, server_url=None, api_user=None,
                api_password=None, timeout=5):
    method = data["method"]
    if method in responses:
        return responses[method]

    raise ripple_api.RippleApiError(
        'Bad request', '',
        'Use only account_lines or account_info methods')


class BalanceTestCase(TestCase):

    def setUp(self):
        self.servers = settings.RIPPLE_API_DATA

    @patch('ripple_api.ripple_api.call_api')
    def test_balance_xrp(self, balance_mock):
        """ Test if balance calls =account_info= rippled-JSON-RPC method
            to obtain XRP Balance
        """

        balance_mock.side_effect = side_effect

        xrp_balance = ripple_api.balance(settings.RIPPLE_ACCOUNT,
                                         issuers=None, currency="XRP",
                                         servers=self.servers)

        self.assertEqual(xrp_balance, Decimal("50.488267"))

    @patch('ripple_api.ripple_api.call_api')
    def test_balance_non_xrp(self, call_api_mock):
        """ Testing if balance calls =account_lies= rippled-JSON-XRP method
            to obtain balances in non XRP currencies
        """

        call_api_mock.side_effect = side_effect
        
        usd_balance = ripple_api.balance(settings.RIPPLE_ACCOUNT,
                                         issuers=None, currency="USD",
                                         servers=self.servers)
        self.assertEqual(usd_balance, Decimal("2.550265201742073"))

        cck_balance = ripple_api.balance(settings.RIPPLE_ACCOUNT,
                                         issuers=None, currency="CCK",
                                         servers=self.servers)
        self.assertEqual(cck_balance, Decimal("7.51418646934461"))
