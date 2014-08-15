# -*- coding: utf-8 -*-

# system imports:
import json
import logging
import socket
from decimal import Decimal
import ssl

# thirdparty imports:
import requests


logger = logging.getLogger(__name__)

ENGINE_SUCCESS = 'tesSUCCESS'


class RippleApiError(Exception):

    def __init__(self, error, code, message):
        self.error = error
        self.code = code
        self.message = message

    def __str__(self):
        return '%s. %s' % (self.error, self.message)


def call_api(data, servers=None, server_url=None, api_user=None, 
             api_password=None):
    try:
        from django.conf import settings
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
    except ImportError:
        if servers is None:
            if server_url:
                servers = [
                    {
                        'RIPPLE_API_URL': server_url,
                        'RIPPLE_API_USER': api_user,
                        'RIPPLE_API_PASSWORD': api_password,
                        }
                    ]
            else:
                raise RippleApiError(
                    'Config', '', 
                    'Either use django settings or send servers explicitly')
        
    error = None
    timeouts = 0

    for server_config in servers:
        url = server_config.get('RIPPLE_API_URL', '')
        user = server_config.get('RIPPLE_API_USER', '')
        pwd = server_config.get('RIPPLE_API_PASSWORD', '')
        auth = (user, pwd) if user or pwd else None
        try:
            response = requests.post(
                url, json.dumps(data), auth=auth, verify=False, timeout=5)
        except TypeError:  # e.g. json encode error
            raise
        except (requests.exceptions.Timeout, ssl.SSLError, socket.timeout) as e:
            timeouts += 1
            continue
        except Exception as e:
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

    if timeouts == len(servers):
        raise RippleApiError('Timeout', '', 'rippled timed out')

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


def path_find(account, destination, amount, source_currencies, servers=None, 
              server_url=None, api_user=None, api_password=None):
    '''
    Before sending IOU you need to find paths to the destination account
    
    Params:
        `account`:
            Source account

        `destination`:
            Destination account

        `amount`:
            IOU amount as in https://ripple.com/wiki/RPC_API#path_find

        `source_currencies`:
            List of source IOU currencies you'd like to pay with
    '''
    data = {'method': 'ripple_path_find',
            'params': [{
                'command': 'ripple_path_find',
                'source_account': account,
                'destination_account': destination,
                'destination_amount': amount,
                'source_currencies': source_currencies,
                }]
        }
    return call_api(data, servers=servers, server_url=server_url, 
                    api_user=api_user, api_password=api_password)

def sign(account, secret, destination, amount, send_max=None, paths=None,
         flags=None, destination_tag=None, transaction_type='Payment',
         servers=None, server_url=None, api_user=None, api_password=None):
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
                    "Amount": amount,
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

    return call_api(data, servers=servers, server_url=server_url, 
                    api_user=api_user, api_password=api_password)


def submit(tx_blob, fail_hard=False, servers=None, server_url=None, 
           api_user=None, api_password=None):
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
            "tx_blob": tx_blob,
            'fail_hard': fail_hard,
            }]}

    return call_api(data, servers=servers, server_url=server_url, 
                    api_user=api_user, api_password=api_password)


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


def is_trust_set(trusts, peer, currency='', limit=0):
    """
    checks if 'trusts' trusts 'peer' with specified currency and limit


    Params:
        `trusts`:
            ripple address, that trusts or not 'peer'
        `peer`:
            ripple_address, that is trusted by  by 'trusts'
        `currency` (optional):
            currency in which trust should be set
        `limit` (optional):
            minimal amount of trust

    Returns boolean

    """
    trust_result = False

    trust_lines = call_api(
        {
            'method': 'account_lines',
            'params': [{
                'account': trusts,
                'peer': peer
            }]
        },
    )

    status = trust_lines['status'] == 'success'
    trusts = trust_lines['lines']
    if status and trusts and not currency:
        trust_result = True

    elif status and trusts and currency:
        for trust in trusts:

            if currency == trust['currency']:
                trust_result = float(limit) <= float(trust['limit'])
                break

    return trust_result


def book_offer(
        taker_pays_curr, taker_pays_curr_issuer, taker_gets_curr, taker_gets_curr_issuer, taker_address='',
        ledger='current', marker='', autobridge=True, server_url=None, api_user=None, api_password=None):
    """
    Gets currency exchange rates

    Params:
        'taker_pays':
            Specified in the following forms 'XRP' or 'USD/rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh'
            The currency and issuer the taker pays. Do not specify an issuing account if the currency is XRP.
        'taker_gets':
            Specified in the following forms 'XRP' or 'USD/rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh'
            The currency and issuer the taker pays. Do not specify an issuing account if the currency is XRP.
        'ledger' (optional):
            "current" (default). "closed", "validated", ledger_index, or ledger.
        'taker' (optional):
            The address of the taker. This affects the funding of offers by owners as they may need to pay transfer fees.
            For a neutral point of view specify ADDRESS_ONE (rrrrrrrrrrrrrrrrrrrrBZbvji).
        'marker' (optional):
            Specify the paging marker as JSON. Defaults to "".
            Token indicating start of page, it is returned from a previous invocation.
        'autobridge' (optional):
            If present, specifies synthesize orders through XRP books. Defaults to true
    """
    taker_pays = 'XRP' if taker_pays_curr == 'XRP' else {"currency": taker_pays_curr, "issuer": taker_pays_curr_issuer}
    taker_gets = 'XRP' if taker_gets_curr == 'XRP' else {"currency": taker_gets_curr, "issuer": taker_gets_curr_issuer}
    data = {
        "method": "book_offers",
        "params": [{
            "taker_pays": taker_pays,
            "taker_gets": taker_gets,
            "ledger": ledger,
            "marker": marker,
            "autobridge": autobridge}]
        }
    if taker_address:
        data["params"][0]["taker"] = taker_address

    return call_api(data, server_url, api_user, api_password)
