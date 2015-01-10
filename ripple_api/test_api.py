# -*- coding: utf-8 -*-
from django.test import TestCase
from django.conf import settings
from django.db.models.signals import post_save

from mock import patch
from requests import ConnectionError, Response
import json
import ssl

from .models import Transaction
from .management.commands.process_transactions import Command
from .signals import transaction_status_changed
from ripple_api import call_api, RippleApiError


class TestRipple(TestCase):

    @patch('ripple_api.ripple_api.call_api')
    def test_monitor_transactions(self, call_api_mock):
        data = {'transactions': [
            {'tx': {'Account': 'account', 'Destination': settings.RIPPLE_ACCOUNT,
                'TransactionType': 'Payment', 'Amount': {'currency': 'CCK', 'issuer': 'p2pay', 'value': '1.2'},
                'hash': 'hash1', 'ledger_index': 1, 'DestinationTag': 232 },
             'meta': {'TransactionResult': 'tesSUCCESS'}},
        ]}
        call_api_mock.return_value = data

        receivers = post_save.receivers
        post_save.receivers = []
        Command().monitor_transactions()
        post_save.receivers = receivers

        self.assertEqual(Transaction.objects.count(), 1)
        transaction = Transaction.objects.get(id=1)
        self.assertEqual(transaction.status, Transaction.RECEIVED)
        self.assertEqual(transaction.account, 'account')
        self.assertEqual(transaction.destination, settings.RIPPLE_ACCOUNT)
        self.assertEqual(transaction.currency, 'CCK')
        self.assertEqual(transaction.issuer, 'p2pay')
        self.assertEqual(transaction.value, '1.2')
        self.assertEqual(transaction.hash, 'hash1')
        self.assertEqual(transaction.destination_tag, 232)


    @patch('ripple_api.tasks.sign')
    @patch('ripple_api.tasks.path_find')
    def test_retry(self, path_find_mock, sign_mock):
        transaction = Transaction.objects.create(
            account='account',
            destination='destination',
            hash='hash',
            status=Transaction.FAILURE,
            currency='XXX',
            tx_blob='tx_blob')

        path_find_mock.return_value = {
            'alternatives': [{
                'paths_computed': [
                    [{u'account': u'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7',
                      u'type': 1,
                      u'type_hex': u'0000000000000001'}],
                ]},
            ],
        }
        sign_mock.return_value = {
            'tx_blob': 'tx_new_blob',
            'tx_json': {
                'hash': 'new_hash'
            }
        }
        Command().retry_failed_transactions()

        transaction = Transaction.objects.get(id=transaction.id)
        self.assertEqual(transaction.status, Transaction.FAIL_FIXED)

        retry_transaction = Transaction.objects.get(hash='new_hash')
        self.assertEqual(retry_transaction.hash, 'new_hash')
        self.assertEqual(retry_transaction.tx_blob, 'tx_new_blob')
        self.assertEqual(retry_transaction.status, Transaction.PENDING)
        self.assertEqual(transaction.value, retry_transaction.value)
        self.assertEqual(transaction.account, retry_transaction.account)
        self.assertEqual(transaction.currency, retry_transaction.currency)
        self.assertEqual(
            transaction.destination,
            retry_transaction.destination
        )
        self.assertEqual(transaction.source_tag, retry_transaction.source_tag)
        self.assertEqual(
            transaction.destination_tag,
            retry_transaction.destination_tag
        )

    @patch('ripple_api.tasks.sign')
    @patch('ripple_api.tasks.path_find')
    def test_return_funds(self, path_find_mock, sign_mock):
        transaction = Transaction.objects.create(
            account='account',
            hash='hash4',
            status=Transaction.MUST_BE_RETURN,
            currency='CCK',
            value='100.1'
        )
        path_find_mock.return_value = {
            'alternatives': [{
                'paths_computed': [
                    [{u'account': u'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7',
                      u'type': 1,
                      u'type_hex': u'0000000000000001'}],
                ]},
            ],
        }
        sign_mock.return_value = {
            'tx_blob': 'tx_blob',
            'tx_json': {
                'hash': 'hash5'
            }
        }

        Command().return_funds()
        returning_transaction = Transaction.objects.get(hash='hash5')

        self.assertEqual(
            returning_transaction.destination,
            transaction.account
        )
        self.assertEqual(returning_transaction.status, Transaction.PENDING)
        self.assertEqual(returning_transaction.tx_blob, 'tx_blob')

        self.assertEqual(returning_transaction.parent, transaction)

    @patch('ripple_api.ripple_api.call_api')
    def test_check_submitted_transactions(self, call_api_mock):
        transaction = Transaction.objects.create(account='account', hash='hash', status=Transaction.RETURNING)
        Transaction.objects.create(account='account', hash='hash1', status=Transaction.SUBMITTED, parent=transaction)

        data = {'meta': {'TransactionResult': 'tesSUCCESS'}}

        call_api_mock.return_value = data
        receivers = transaction_status_changed.receivers
        transaction_status_changed.receivers = []
        Command().check_submitted_transactions()
        transaction_status_changed.receivers = receivers

        transaction = Transaction.objects.get(hash='hash1')
        self.assertEqual(transaction.status, Transaction.SUCCESS)
        self.assertEqual(transaction.parent.status, Transaction.RETURNED)

    @patch('ripple_api.ripple_api.call_api')
    def test_submit_pending(self, call_api_mock):
        Transaction.objects.create(
                account='account',
                hash='hash',
                status=Transaction.PENDING,
                tx_blob='tx_blob')
        data = {'engine_result': 'tesSUCCESS'}

        call_api_mock.return_value = data
        Command().submit_pending_transactions()
        transaction = Transaction.objects.get(hash='hash')
        self.assertEqual(transaction.status, Transaction.SUBMITTED)

    @patch('requests.post')
    def test_call_api(self, post_mock):
        original_settings = settings.RIPPLE_API_DATA
        settings.RIPPLE_API_DATA = [
            {
                'RIPPLE_API_URL': 'http://one.ripple.com:51234',
                'RIPPLE_API_USER': '',
                'RIPPLE_API_PASSWORD': '',
            },
            {
                'RIPPLE_API_URL': 'http://two.ripple.com:51234',
                'RIPPLE_API_USER': '',
                'RIPPLE_API_PASSWORD': '',
            },
            {
                'RIPPLE_API_URL': 'http://three.ripple.com:51234',
                'RIPPLE_API_USER': '',
                'RIPPLE_API_PASSWORD': '',
            }
        ]

        def custom_call_api(error):
            try:
                call_api({})
            except error:
                self.assertEqual(post_mock.call_count,
                                 len(settings.RIPPLE_API_DATA))

        def side_effect(*args, **kwargs):
            raise ConnectionError

        post_mock.side_effect = side_effect

        custom_call_api(ConnectionError)

        def side_effect(*args, **kwargs):
            response = Response()
            response._content = '''{'\2': 'binary', 'result': 'failed'}'''
            return response

        post_mock.reset_mock()
        post_mock.side_effect = side_effect

        custom_call_api(RippleApiError)

        def side_effect(*args, **kwargs):
            response = Response()
            response_data = {'result': {}}
            response_data['result']['error'] = 'failed'
            response_data['result']['error_code'] = 403
            response_data['result']['error_message'] = 'You failed!'
            response._content = json.dumps(response_data)
            return response

        post_mock.reset_mock()
        post_mock.side_effect = side_effect

        custom_call_api(RippleApiError)

        settings.RIPPLE_API_DATA = original_settings

    @patch('requests.post')
    def test_timeout(self, post_mock):
        post_mock.side_effect = ssl.SSLError

        with self.assertRaises(RippleApiError):
            call_api({})
