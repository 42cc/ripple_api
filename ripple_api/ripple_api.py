# -*- coding: utf-8 -*-

# system imports:
import json
import logging
from decimal import Decimal

# thirdparty imports:
import requests
from django.conf import settings


logger = logging.getLogger(__name__)

ENGINE_SUCCESS = 'tesSUCCESS'


class RippleApiError(Exception):

    def __init__(self, error, code, message):
        self.error = error
        self.code = code
        self.message = message

    def __str__(self):
        return '%s. %s' % (self.error, self.message)


def call_api(data, server_url=None, api_user=None, api_password=None):
    error = None
    if server_url and not (api_user or api_password):
        servers = filter(
            lambda item: item.get('RIPPLE_API_URL', '') == server_url,
            settings.RIPPLE_API_DATA
        )
        servers = servers or [{'RIPPLE_API_URL': server_url}]
    elif server_url and (api_user or api_password):
        servers = [
            {
                'RIPPLE_API_URL': server_url,
                'RIPPLE_API_USER': api_user,
                'RIPPLE_API_PASSWORD': api_password,
            }
        ]
    else:
        servers = settings.RIPPLE_API_DATA

    for server_config in servers:
        url = server_config.get('RIPPLE_API_URL', '')
        user = server_config.get('RIPPLE_API_USER', '')
        pwd = server_config.get('RIPPLE_API_PASSWORD', '')
        auth = (user, pwd) if user or pwd else None
        try:
            response = requests.post(
                url, json.dumps(data), auth=auth, verify=False, timeout=5)
        except requests.ConnectionError, e:
            error = e
            continue

        try:
            result = response.json()['result']
        except ValueError:
            error = RippleApiError('Error', '', response.text)
            continue

        if not 'error' in result:
            return result
        else:
            error = RippleApiError(
                result['error'],
                result.get('error_code', 'no_code'),
                result.get('error_message', 'no_message'),
            )
            continue
    raise error


def account_tx(
        account, ledger_index_min=-1, ledger_index_max=-1, binary=False,
        forward=False, limit=None, marker=None,
        server_url=None, api_user=None, api_password=None):
    """
    Fetch a list of transactions that applied to this account.

    Params:
        `account`:
            Ripple account.

        `ledger_index_min` or `ledger_index_max` of -1 indicates the first and last fully-validated ledgers the server
            has available. This range may not be stable. If you've gotten a count this way and you wish to query the
            same set, make sure to use the returned ledger_index_min and ledger_index_max on future queries.

        `binary`:
            True, to return transactions in hex rather than JSON.

        `forward`:
            True, to sort in ascending ledger order.

        `limit`:
            Maximum number of results to provide.

        `marker`:
            The point to resume from.

    """
    data = {"method": "account_tx",
            "params": [{
                "account": account,
                "ledger_index_min": ledger_index_min,
                "ledger_index_max": ledger_index_max,
                "binary": binary,
                "forward": forward}]}
    if limit:
        data['params'][0]['limit'] = limit
    if marker:
        data['params'][0]['marker'] = marker

    return call_api(data, server_url, api_user, api_password)


def tx(transaction_id, server_url=None, api_user=None, api_password=None):
    """
    Return information about a transaction.

    Params:

        `transaction_id`:
            Hash of transaction.
    """
    data = {"method": "tx",
            "params": [{'transaction': transaction_id}]}

    return call_api(data, server_url, api_user, api_password)


def sign(
        account, secret, destination, amount, send_max=None, paths=None,
        flags=None, destination_tag=None, transaction_type='Payment',
        server_url=None, api_user=None, api_password=None):
    """
    After you've created a transaction it must be cryptographically signed using the secret belonging to the owner of
    the sending address. Signing a transaction prior to submission allows you to maintain closer control over
    transaction history. It also allows you to resubmit a previous transaction in the case of a connection failure
    without needing to set up another transaction.

    Params:
        `account`:
            Ripple account.

        `secret`:
            Secret key of sender.

        `destination`:
            The receiving account.

        `amount`:
            The amount and currency for the destination to receive.

            If currency is  XRP, then amount is simply value of payment.
            In other cases, amount have that format:
            {
              "currency" : currency,
              "value" : string,
              "issuer" : account_id,
            }

            To deliver a specific issuer's currency, set the issuer to the account of the issuer.
            To not specify a specific issuer, set the issuer to the receiving account.

        `destination_tag`:
            Tag to identify the reason for payment.
    """
    data = {
        "method": "sign",
        "params": [
            {
                "secret": secret,
                "tx_json":
                {
                    "TransactionType": transaction_type,
                    "Account": account,
                    "Destination": destination,
                    "Amount": amount
                }
            }]}

    if send_max:
        data['params'][0]['tx_json']['SendMax'] = send_max
    if paths:
        data['params'][0]['tx_json']['Paths'] = paths
    if flags:
        data['params'][0]['tx_json']['Flags'] = flags
    if destination_tag:
        data['params'][0]['tx_json']['DestinationTag'] = destination_tag

    return call_api(data, server_url, api_user, api_password)


def submit(tx_blob, server_url=None, api_user=None, api_password=None):
    """
    Submits a transaction to the network.

    Params:
        `tx_blob`:
            It  is the signed, encrypted transaction request generated by call of sign is represented as a very long
             string of hexadecimal digits(several hundred characters in length).

    """
    data = {
        "method": "submit",
        "params": [{
            "tx_blob": tx_blob}]}

    return call_api(data, server_url, api_user, api_password)


def balance(
        account, issuers, currency,
        server_url=None, api_user=None, api_password=None):
    results = call_api(
        {
            'method': 'account_lines',
            'params': [{'account': account}]
        },
        server_url=None, api_user=None, api_password=None
    )
    total = Decimal('0.0')
    for line in results['lines']:
        if line['currency'] == currency and (line['account'] in issuers or issuers is None):
            total += Decimal(line['balance'])
    return total
