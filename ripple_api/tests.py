# -*- coding: utf-8 -*-
from django.test import TestCase
from django.conf import settings
from django.db.models.signals import post_save

from mock import patch

from .models import Transaction
from .management.commands.process_transactions import Command
from .signals import transaction_status_changed


class TestRipple(TestCase):

    @patch('ripple_api.ripple_api.call_api')
    def test_monitor_transactions(self, call_api_mock):
        data = {'transactions': [
            {'tx': {'Account': 'account', 'Destination': settings.RIPPLE_ACCOUNT,
                'TransactionType': 'Payment', 'Amount': {'currency': 'CCK', 'issuer': 'p2pay', 'value': '1.2'},
                'hash': 'hash1', 'ledger_index': 1, 'DestinationTag': 232 }},
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


    @patch('ripple_api.ripple_api.call_api')
    def test_retry(self, call_api_mock):
        transaction = Transaction.objects.create(
            account='account',
            destination='destination',
            hash='hash',
            status=Transaction.FAILURE,
            tx_blob='tx_blob')


        def side_effect():
            yield {'tx_blob': 'new_tx_blob',
                    'tx_json': {
                        'hash': 'new_hash'
                    }}
            yield {'engine_result': 'tesSUCCESS'}

        call_api_mock.side_effect = side_effect()
        Command().retry_failed_transactions()
        transaction = Transaction.objects.get(id=transaction.id)
        self.assertEqual(transaction.status, Transaction.SUBMITTED)
        self.assertEqual(transaction.hash, 'new_hash')
        self.assertEqual(transaction.tx_blob, 'new_tx_blob')

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