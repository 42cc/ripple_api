# -*- coding: utf-8 -*-

from decimal import Decimal
from django.test import TestCase

from mock import patch

from trade import sell_all

part_pay = 0.5
part_get = 0.1
amount_get = 1
amount_pay = 2
sequence = 1
balance_pay = 100
balance_get = 200

AffectedNodes = {
    u'DeletedNode': {
        'LedgerEntryType': 'Offer',
        'PreviousFields': {
            u'TakerPays': {
                u'currency': 'TUS',
                u'value': str(part_pay),
                u'issuer': u'rJobmmpNqozqY7MzwGkRs1VLEBJ7H5Pjrp'
            },
            u'Account': u'rJobmmpNqozqY7MzwGkRs1VLEBJ7H5Pjrp',
            u'TakerGets': {
                u'currency': 'TBT',
                u'value': str(part_get),
                u'issuer': u'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
            },
        }
    },
}
data = {
    u'status': u'success',
    u'engine_result': u'tesSUCCESS',
    u'engine_result_message': u'The transaction was applied.',
    u'engine_result_code': 0,
    u'tx_blob': u'test',
    u'tx_json': {
        u'Account': settings.RIPPLE_ACCOUNT,
        u'hash': u'test_hash',
        u'Sequence': sequence,
        u'TakerPays': {
            u'currency': 'TBT',
            u'value': amount_pay,
            u'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
        },
        u'TakerGets': {
            u'currency': 'TUS',
            u'value': amount_get,
            u'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7',
            u'TransactionType': u'OfferCreate'
        }
    }
}

tx_data = {
    u'status': u'success',
    u'Account': settings.RIPPLE_ACCOUNT,
    u'Sequence': sequence,
    u'TakerPays': {
        u'currency': 'TBT',
        u'value': str(amount_pay),
        u'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
    },
    u'meta': {
        u'TransactionResult': u'tesSUCCESS',
        u'AffectedNodes': [{
            u'ModifiedNode': {
                u'LedgerEntryType': u'Offer',
                u'FinalFields': {
                    u'Account': u'rfaqM2Mkc9UT2RAWvLFfUivUqhyH4i5qgd',
                    u'Sequence': sequence,
                    u'TakerPays': {
                        u'currency': 'TUS',
                        u'value': str(amount_pay),
                        u'issuer': u'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
                    },
                    u'TakerGets': {
                        u'currency': 'TBT',
                        u'value': str(amount_get),
                        u'issuer': u'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
                    },
                    u'Flags': 0
                },
                u'PreviousFields': {
                    u'TakerPays': {
                        u'currency': 'TUS',
                        u'value': str(balance_pay),
                        u'issuer': u'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
                    },
                    u'TakerGets': {
                        u'currency': 'TBT',
                        u'value': str(balance_get),
                        u'issuer': u'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
                    }
                }
            }
        }]
    },
    u'TakerGets': {
        u'currency': 'TUS',
        u'value': str(amount_get),
        u'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7',
    },
    u'validated': True,
    u'TransactionType': u'OfferCreate'
}


def generate_ripple_transaction_meta(final_balance, previous_balance):
    return {
        'AffectedNodes': [
            {
                "ModifiedNode": {
                    "FinalFields": {
                        "Balance": {
                            "currency": "TUS",
                            "issuer": "rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7",
                            "value": str(final_balance)
                        },
                        "HighLimit": {
                            "currency": "TUS",
                            "issuer": 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7',
                            "value": "10000"
                        },
                    },
                    "LedgerEntryType": "RippleState",
                    "PreviousFields": {
                        "Balance": {
                            "currency": "TUS",
                            "issuer": "rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7",
                            "value": str(previous_balance)
                        }
                    },
                }
            },
            {
                "ModifiedNode": {
                    "FinalFields": {
                        "Account": settings.RIPPLE_ACCOUNT,
                        "Balance": "80678117",
                    },
                    "LedgerEntryType": "AccountRoot",
                    "PreviousFields": {
                        "Balance": "80688117",
                        "Sequence": 959
                    },
                }
            },
            {
                "ModifiedNode": {
                    "FinalFields": {
                        "Balance": {
                            "currency": "TUS",
                            "issuer": "rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7",
                            "value": "0.1"
                        },
                        "HighLimit": {
                            "currency": "TUS",
                            "issuer": "rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7",
                            "value": "0"
                        },
                    },
                    "LedgerEntryType": "RippleState",
                    "PreviousFields": {
                        "Balance": {
                            "currency": "TUS",
                            "issuer": "rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7",
                            "value": "0.2"
                        }
                    },
                }
            }
        ],
        'TransactionResult': 'tesSUCCESS'
    }


class TradeTestCase(TestCase):
    def setUp(self):
        self.create_data = data
        self.tx_data = tx_data

    @patch('ripple_api.call_api')
    @patch('trade.create_offer')
    def test_offer_create_error(self, create_offer_mock, call_api_mock):
        """Test if do not sell all when has error in offer."""
        self.create_data['engine_result'] = 'error'

        create_offer_mock.return_value = self.create_data
        call_api_mock.return_value = self.create_data

        exchange_result = sell_all(
            sell_needed={
                'value': amount_pay, 'currency': 'TUS',
                'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
            },
            buy_expected={
                'value': amount_get, 'currency': 'TBT',
                'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
            },
        )

        # check result error, sold 0, bought 0
        self.assertEqual(exchange_result['status'], 'error')
        self.assertEqual(exchange_result['status_msg'],
                         'Offer creation failed: error')
        self.assertEqual(exchange_result['sold'], 0)
        self.assertEqual(exchange_result['bought'], 0)

    @patch('ripple_api.call_api')
    @patch('trade.create_offer')
    def test_offer_create_nothing_happened(self, create_offer_mock,
                                           call_api_mock):
        """Test if do not sell all when offer without data 'AffectedNodes'."""
        self.create_data['engine_result'] = 'tesSUCCESS'
        rez = self.tx_data['meta']['AffectedNodes']
        del self.tx_data['meta']['AffectedNodes']

        create_offer_mock.return_value = self.create_data

        call_api_mock.return_value = self.tx_data

        exchange_result = sell_all(
            sell_needed={
                'value': amount_pay, 'currency': 'TUS',
                'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
            },
            buy_expected={
                'value': amount_get, 'currency': 'TBT',
                'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
            },
        )
        self.tx_data['meta']['AffectedNodes'] = rez
        # check result success, sold 0, bought 0
        self.assertEqual(exchange_result['status'], 'error')
        self.assertEqual(exchange_result['status_msg'],
                         "Offer was not identified.")
        self.assertEqual(exchange_result['sold'], 0)
        self.assertEqual(exchange_result['bought'], 0)

    @patch('ripple_api.call_api')
    @patch('trade.create_offer')
    def test_offer_create_not_happened(self, create_offer_mock, call_api_mock):
        """Test if do not sell all when offer without data 'ModifiedNode'."""
        self.create_data['engine_result'] = 'tesSUCCESS'
        rez = self.tx_data['meta']['AffectedNodes'][0]['ModifiedNode']
        del self.tx_data['meta']['AffectedNodes'][0]['ModifiedNode']

        create_offer_mock.return_value = self.create_data

        call_api_mock.return_value = self.tx_data

        exchange_result = sell_all(
            sell_needed={
                'value': amount_pay, 'currency': 'TUS',
                'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
            },
            buy_expected={
                'value': amount_get, 'currency': 'TBT',
                'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
            },
        )
        self.tx_data['meta']['AffectedNodes'][0]['ModifiedNode'] = rez
        # check result success, sold 0, bought 0
        self.assertEqual(exchange_result['status'], 'success')
        self.assertEqual(exchange_result['sold'], 0)
        self.assertEqual(exchange_result['bought'], 0)

    @patch('ripple_api.call_api')
    @patch('trade.create_offer')
    def test_offer_create_sold_a_part(self, create_offer_mock, call_api_mock):
        """Test if correct sell a part, when offer has only part for sell."""
        self.create_data['engine_result'] = 'tesSUCCESS'
        create_offer_mock.return_value = self.create_data

        call_api_mock.return_value = self.tx_data

        exchange_result = sell_all(
            sell_needed={
                'value': amount_pay, 'currency': 'TUS',
                'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
            },
            buy_expected={
                'value': amount_get, 'currency': 'TBT',
                'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
            },
        )

        # check result success, sold only a part
        self.assertEqual(exchange_result['status'], 'success')
        self.assertEqual(exchange_result['bought'],
                         Decimal(balance_get - amount_get))
        self.assertEqual(exchange_result['sold'],
                         Decimal(balance_pay - amount_pay))

    @patch('ripple_api.call_api')
    @patch('trade.create_offer')
    def test_offer_create_sold_everything(self, create_offer_mock,
                                          call_api_mock):
        """Test if correct we can sell all."""

        self.create_data['engine_result'] = 'tesSUCCESS'
        del self.tx_data['meta']['AffectedNodes'][0]['ModifiedNode']

        self.tx_data['meta']['AffectedNodes'][-1] = AffectedNodes

        create_offer_mock.return_value = self.create_data

        call_api_mock.return_value = self.tx_data

        exchange_result = sell_all(
            sell_needed={
                'value': amount_pay, 'currency': 'TUS',
                'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
            },
            buy_expected={
                'value': amount_get, 'currency': 'TBT',
                'issuer': 'rp2PaYDxVwDvaZVLEQv7bHhoFQEyX1mEx7'
            },
        )

        # check result success, sold a part
        self.assertEqual(exchange_result['status'], 'success')
        self.assertEqual(exchange_result['sold'], Decimal("%.6f" % part_pay))
        self.assertEqual(exchange_result['bought'], Decimal("%.6f" % part_get))
