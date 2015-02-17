# -*- coding: utf-8 -*-
import json

from django.conf import settings
from django.test import TestCase

from requests import Response

from mock import patch

from .ripple_api import trust_set, RippleApiError

sequence = 12
destination_account = u'rJobmmpNqozqY7MzwGkRs1VLEBJ7H5Pjrp'
wrong_secret = "somesecret"

data = {
    u"engine_result": u"tesSUCCESS",
    u"engine_result_code": 0,
    u"engine_result_message": (u"The transaction was applied. Only final " +
                               u"in a validated ledger."),
    u"status": u"success",
    u"tx_blob": u"-- hexBinary data --",
    u"tx_json": {
        u"Account": settings.RIPPLE_ACCOUNT,
        u"Fee": u"10000",
        u"Flags": 262144,
        u"LimitAmount": {
            u"currency": u"USD",
            u"issuer": destination_account,
            u"value": u"1"
        },
        u"Sequence": sequence,
        u"SigningPubKey": u"-- hexBinary data of SigningPubKey --",
        u"TransactionType": u"TrustSet",
        u"TxnSignature": u"-- hexBinary data of TxnSignature --",
        u"hash": u"-- hexBinary data of hash --"
    }
}

error_data = {
    u"error": "badSecret",
    u"error_code": 39,
    u"error_message": "Secret does not match account.",
    u"request": {
        u"command": u"submit",
        u"secret": wrong_secret,
        u"tx_json": {
            u"Account": settings.RIPPLE_ACCOUNT,
            u"Fee": "10000",
            u"Flags": 262144,
            u"LimitAmount": {
                u"currency": "USD",
                u"issuer": destination_account,
                u"value": "1"
            },
            u"TransactionType": "TrustSet"
        }
    },
    u"status": "error"
}


class TrustSetTestCase(TestCase):

    def setUp(self):
        pass

    @patch('requests.post')
    def test_trust_set_error(self, post_mock):
        """Test if RippleApiError raised in case when secret is wrong"""
        response = Response()
        response._content = json.dumps({u"result": error_data})
        post_mock.return_value = response

        exp_msg = u'39: badSecret. Secret does not match account.'
        with self.assertRaisesMessage(RippleApiError, exp_msg):
            trust_set(
                settings.RIPPLE_ACCOUNT, wrong_secret,
                destination_account,
                1, u"USD", flags={"AllowRipple": False, "Freeze": True}
            )

    @patch('requests.post')
    def test_trust_set_success(self, post_mock):
        response = Response()
        response._content = json.dumps({u"result": data})
        post_mock.return_value = response

        result = trust_set(
            settings.RIPPLE_ACCOUNT, settings.RIPPLE_SECRET,
            destination_account,
            1, u"USD", flags={"AllowRipple": True}
        )

        self.assertDictEqual(result, data)
