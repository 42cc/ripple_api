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

'''
   Trust lines flags definition
   Docs: https://ripple.com/build/transactions/#trustset
'''
# Authorize the other party to hold issuances from this
# account. (No effect unless using the asfRequireAuth
# AccountSet flag.) Cannot be unset.
#
# For details see:
# https://ripple.com/build/transactions/#accountset-flags
SET_AUTH = 0x00010000        # tfSetAuth = 65536

# Blocks rippling between two trustlines of the same currency,
# if this flag is set on both. (See No Ripple for details.)
#
# For details see:
# https://ripple.com/knowledge_center/understanding-the-noripple-flag/
SET_NORIPPLE = 0x00020000    # tfSetNoRipple = 131072

# Clears the No-Rippling flag. (See No Ripple for details.)
#
# For details see:
# https://ripple.com/knowledge_center/understanding-the-noripple-flag/
CLEAR_NORIPPLE = 0x00040000   # tfClearNoRipple = 262144

# Freeze the trustline.
#
# For details see:
# https://wiki.ripple.com/Freeze
SET_FREEZE = 0x00100000      # tfSetFreeze = 1048576

# Unfreeze the trustline
#
# For details see:
# https://wiki.ripple.com/Freeze
CLEAR_FREEZE = 0x00200000    # tfClearFreeze = 2097152

# No flags set
NO_FLAGS = 0x0000000
'''
    end of Trust lines flags definition
'''


class RippleApiError(Exception):

    def __init__(self, error, code, message):
        self.error = error
        self.code = code
        self.message = message

    def __str__(self):
        return '%s: %s. %s' % (self.code, self.error, self.message)


def call_api(data, servers=None, server_url=None, api_user=None,
             api_password=None, timeout=5):
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
            from django.core.exceptions import ImproperlyConfigured
            # we have django in virtual env, but not necessarily 
            # a settings.RIPPLE_API_DATA
            try:
                servers = settings.RIPPLE_API_DATA
            except ImproperlyConfigured:
                raise ImportError
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
                url, json.dumps(data), auth=auth, verify=False, timeout=timeout)
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
        server_url=None, api_user=None, api_password=None, timeout=5):
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

    return call_api(data, server_url, api_user, api_password, timeout=timeout)


def tx(transaction_id, servers=None, server_url=None, api_user=None,
       api_password=None, timeout=5):
    """
    Return information about a transaction.

    Params:

        `transaction_id`:
            Hash of transaction.
    """
    data = {"method": "tx",
            "params": [{'transaction': transaction_id}]}

    return call_api(data, servers=servers, server_url=server_url,
                    api_user=api_user, api_password=api_password,
                    timeout=timeout)


def path_find(account, destination, amount, source_currencies, servers=None,
              server_url=None, api_user=None, api_password=None, timeout=5):
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
                    api_user=api_user, api_password=api_password,
                    timeout=timeout)


def sign(account, secret, destination, amount, send_max=None, paths=None,
         flags=None, destination_tag=None, transaction_type='Payment',
         servers=None, server_url=None, api_user=None, api_password=None,
         timeout=5, fee=10000):
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
                    "Fee": fee,
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
                    api_user=api_user, api_password=api_password,
                    timeout=timeout)


def submit(tx_blob, fail_hard=False, servers=None, server_url=None,
           api_user=None, api_password=None, timeout=5):
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
                    api_user=api_user, api_password=api_password,
                    timeout=timeout)


def balance(account, issuers, currency, servers=None, server_url=None,
            api_user=None, api_password=None, timeout=5):
    results = call_api({'method': 'account_lines',
                        'params': [{'account': account}]
                        },
                       servers=servers,
                       server_url=server_url,
                       api_user=api_user,
                       api_password=api_password,
                       timeout=timeout,
                       )
    total = Decimal('0.0')
    for line in results['lines']:
        if line['currency'] == currency:
            if issuers is None or line['account'] in issuers:
                total += Decimal(line['balance'])
    return total


def is_trust_set(trusts, peer, currency='', limit=0, timeout=5):
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
        timeout=timeout,
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
    ledger='current', marker='', autobridge=True, server_url=None,
    api_user=None, api_password=None, timeout=5):
    """
    Gets currency exchange rates

    Params:
        'taker_pays':
            Specified in the following forms 'XRP' or 'USD/rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh'
            The currency and issuer the taker pays.
            Do not specify an issuing account if the currency is XRP.
        'taker_gets':
            Specified in the following forms 'XRP' or 'USD/rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh'
            The currency and issuer the taker pays. Do not specify an issuing
            account if the currency is XRP.
        'ledger' (optional):
            "current" (default). "closed", "validated", ledger_index, or ledger.
        'taker' (optional):
            The address of the taker. This affects the funding of offers by
            owners as they may need to pay transfer fees.
            For a neutral point of view specify ADDRESS_ONE (rrrrrrrrrrrrrrrrrrrrBZbvji).
        'marker' (optional):
            Specify the paging marker as JSON. Defaults to "".
            Token indicating start of page, it is returned from a previous invocation.
        'autobridge' (optional):
            If present, specifies synthesize orders through XRP books. Defaults to true
    """
    taker_pays = 'XRP' if taker_pays_curr == 'XRP' else {
        "currency": taker_pays_curr, "issuer": taker_pays_curr_issuer
    }
    taker_gets = 'XRP' if taker_gets_curr == 'XRP' else {
        "currency": taker_gets_curr, "issuer": taker_gets_curr_issuer
    }
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

    return call_api(data, server_url, api_user, api_password, timeout=timeout)


def create_offer(taker_pays, taker_gets,
                 account=None,
                 secret=None,
                 timeout=5,
                 fee=10000, flags=0):
    """
    taker - user, that accepts your offer
    takes:
        taker_pays -  {
            'amount':   - float - amount to buy
            'currency': - str   - currency
            'issuer':   - str   - issuer
        }
        or Decimal(amount) if currency is XRP
        taker_gets -  {
            'amount':   - float - amount to sell
            'currency': - str   - currency
            'issuer':   - str   - issuer
        }
        or Decimal(amount) if currency is XRP
    """

    if isinstance(taker_pays, dict):
        taker_pays['amount'] = "%.12f" % taker_pays['amount']
    else:
        taker_pays = "%.12f" % taker_pays
    if isinstance(taker_gets, dict):
        taker_gets['amount'] = "%.12f" % taker_gets['amount']
    else:
        taker_gets = "%.12f" % taker_gets
    offer = {
        "method": "submit",
        "params": [{
            "secret": secret,
            "tx_json": {
                "TransactionType": "OfferCreate",
                "Fee": str(fee),
                "Flags": flags,
                "Account": account,
                "TakerPays": taker_pays,
                "TakerGets": taker_gets,
            },
        }]
    }

    return call_api(offer, timeout=timeout)


def convert(amount_from,
            currency_from, issuer_from,
            currency_to, issuer_to,
            taker_address='', offers_info='',
            call_offer=True, default_rate=0,
            sell=False, reverse=False):

    offers_all = []
    if reverse:
        currency_from, currency_to = currency_to, currency_from
        issuer_from, issuer_to = issuer_to, issuer_from

    def check_offers(offers_info):
        status = offers_info['status']
        offers_all = offers_info['offers']
        if not offers_all:
            status = 'no_offers'
        return status, offers_all

    # find offers from provided
    if offers_info:
        status, offers_all = check_offers(offers_info)

    if not offers_all and call_offer:
        try:
            offers_info = book_offer(
                currency_from, issuer_from, currency_to, issuer_to,
                taker_address=taker_address,
            )
            # conn_status = offers_info['status']
            status, offers_all = check_offers(offers_info)
        except Exception:
            status = 'error'

    # convert
    amount_to = 0
    if offers_all:
        convert_left = Decimal(amount_from)
        for offer in offers_all:
            if 'taker_gets_funded' in offer:
                pays = Decimal(extract_value(offer['taker_pays_funded']))
                gets = Decimal(extract_value(offer['taker_gets_funded']))
            else:
                pays = Decimal(extract_value(offer['TakerPays']))
                gets = Decimal(extract_value(offer['TakerGets']))

            if not sell:
                if convert_left < gets:
                    rate = Decimal(offer['quality'])
                    amount_to += convert_left * rate
                    convert_left = 0
                    break
                convert_left -= gets
                amount_to += pays
            else:
                if convert_left < pays:
                    rate = Decimal(offer['quality'])
                    amount_to += convert_left / rate
                    convert_left = 0
                    break
                convert_left -= pays
                amount_to += gets

        status = 'success'
        if convert_left:
            rate = Decimal(offers_all[-1]['quality'])
            amount_to += convert_left * rate if not sell else convert_left / rate
            status = 'attn_not_enough_funds'

    # get default rate if nothing found
    elif not offers_all and default_rate:
        status = 'default' if not status else status
        amount_to = Decimal(default_rate) * Decimal(amount_from)

    return {'status': status,
            'amount_to': Decimal(amount_to)}


def extract_value(taker_pays_or_gets):
    if isinstance(taker_pays_or_gets, dict):
        return taker_pays_or_gets['value']
    return taker_pays_or_gets


def _error(resp):
    return {'status': resp['status'],
            'status_msg': resp['error_message']
            }

def buy_xrp(amount, account, secret, servers=None):
    """Trade USD -> XRP.

    - amount: amount of XRP to buy in drops (1000000 = 1 XRP)
    - account: ripple account
    - secret: account's secret
    """
    logger.info("Trying to find paths")
    paths = path_find(account, account, "%s" % amount, [{"currency": "USD"}],
                      servers=servers)
    if paths['status'] != 'success':
        logger.error('Failed to find paths')
        return _error(paths)

    logger.info("Paths found successfully")
    logger.info("Trying to sign transaction")

    if len(paths['alternatives']) == 0:
        msg = u'No path alternatives (probably no USD or no offers)'
        paths['status'] = 'error'
        paths['error_message'] = msg
        logger.error(msg)
        return _error(paths)
    send_max = paths['alternatives'][0]['source_amount']
    result = sign(account, secret, account, amount,
                  send_max=send_max,
                  paths=paths['alternatives'][0]['paths_computed'],
                  flags=0, servers=servers)
    if result['status'] != 'success':
        logger.error('Failed to sign the transaction')
        return _error(result)

    logger.info("Transaction was successfully signed")
    logger.info("Trying to submit transaction")

    blob = result['tx_blob']
    result = submit(blob, servers=servers)
    if result['status'] != 'success':
        return {'status': result['status'],
                'status_msg': result['error']}

    logger.info("Transaction was successfully submitted")

    return {'status': 'success',
            'bought': amount,
            'sold': send_max['value']}


def trust_set(account, secret, destination, amount, currency,
              flags=NO_FLAGS, destination_tag=None,
              servers=None, server_url=None, api_user=None, api_password=None,
              timeout=5, fee=10000):
    """
        Creates, updates or deletes trust line from account to destination
        with amount of currency

        Documentation:
        https://ripple.com/build/transactions/#trustset

        takes:

            account -- id of the ripple account trusts

            secret -- the secret of account trusts

            destination -- id of the ripple account must be trust to

            amount -- amount of trust limit. if Amount is 0 trust line will
                      be deleted from account to destination

            currency -- currency of trust line

            fee -- (optional) XRP drops of ripple fee. Default = 10000 drops

            flags -- (optional) integer or dictionary - {
                "Auth":
                    True, # tfSetAuth - equals to increase flags by SET_AUTH
                "AllowRipple":
                    False, # tfSetNoRipple - equals to increase flags
                           # by SET_NORIPPLE
                    True, # tfClearNoRipple - equals to increase
                          # flags by CLEAR_NORIPPLE
                "Freeze":
                    True, # tfSetFreeze - equals to increase flags
                          # by SET_FREEZE
                    False, # tfClearFreeze - equals to increase flags
                           # by CLEAR_FREEZE
            }. Default equals to { } (empty dictionary)

            destination_tag -- (optional) the tag to explain the transaction

            servers -- (optional) the list of servers to be called to submit
                       transaction

        returns: result field form json-response of rippled server

    """
    if isinstance(flags, dict):
        flags = (
            # tfSetAuth
            (SET_AUTH if flags.get("Auth", False) else 0) +

            # tfClearNoRipple
            (CLEAR_NORIPPLE if flags.get("AllowRipple", None) else 0) +

            # tfSetNoRipple
            (SET_NORIPPLE if not flags.get("AllowRipple", True) else 0) +

            # tfSetFreeze
            (SET_FREEZE if flags.get("Freeze", None) else 0) +

            # tfClearFreeze
            (CLEAR_FREEZE if not flags.get("Freeze", True) else 0)
        )

    trustset = {
        "method": "submit",
        "params": [{
            "secret": secret,
            "tx_json": {
                "TransactionType": "TrustSet",
                "Fee": str(fee),
                "Flags": flags,
                "Account": account,
                "LimitAmount": {
                    "currency": currency,
                    "issuer": destination,
                    "value": "%.2f" % amount
                }
            },
        }]
    }

    logger.info("Trying to submit TrustSet")

    result = call_api(trustset,
                      servers=servers, server_url=server_url,
                      api_user=api_user, api_password=api_password,
                      timeout=timeout
                      )

    if result['status'] == 'success':
        logger.info("TrustSet was successfully submitted")

    return result
