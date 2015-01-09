# -*- coding: utf-8 -*-

from decimal import Decimal
import time
import logging
import os
from distutils.util import strtobool

from ripple_api import call_api, tx

logger = logging.getLogger('ripple_trade')


def sell_all(buy_expected, sell_needed,
             account, secret, timeout=5, fee=10000,
             default_precission=Decimal('0.00000001'),
             servers=None):
    """
    Exchange the entire sell needed amount, even if it means obtaining more
    than the buy expected amount in exchange.

    takes:
    buy_expected -  {
        'value:     - Decimal - min amount to buy
        'currency': - str     - currency
        'issuer':   - str     - issuer
    }
    sell_needed -  {
        'value':    - Decimal - amount to sell
        'currency': - str     - currency
        'issuer':   - str     - issuer
    }
    account            - ripple account
    secret             - ripple secret
    timeout            - trade timeout (default: 5)
    fee                - ripple fee (default: 10000)
    default_precission - compare precission(default: 0.00000001)
    servers            - ripple servers (default: none)

    returns: {
        'status':      - str    - 'success' / 'error',
        'status_msg':  - str    - 'status description'
        'sold':        - float  - the amount sold
        'bought':      - float  - the amount bought
    }

    """
    logger.info('Trading %s %s -> %s %s' %
                (sell_needed['value'], sell_needed['currency'],
                 buy_expected['value'], buy_expected['currency']))
    offer = sell_all_or_cancel(buy_expected, sell_needed, account, secret,
                               timeout=timeout, fee=fee, servers=servers)
    offer_result = get_trade_result(offer, timeout, servers)
    offer_result['sell_amount_left'] = Decimal(
        "%.12f" % float(sell_needed['value'] - offer_result['sold']))

    if offer_result['sold'] >= sell_needed['value'] - default_precission:
        logger.info("Trade fully funded")
    elif offer_result['sold']:
        logger.info("Trade partially happen")
    else:
        logger.info("Trade didn't happen")

    return offer_result


def get_trade_result(created_offer, timeout, servers=None):
    """
    Get created offer result and process it to human readable format.

    takes:
        ripple offer result returned by CreateOffer call

    returns: {
        'status':      - str   - 'success' / 'error',
        'status_msg':  - str   - 'status description'
        'sold':        - float - the amount sold
        'bought':      - float - the amount bought
    }

    """
    # check offer result
    if not created_offer or created_offer['engine_result'] != 'tesSUCCESS':

        status_msg = "Offer creation failed: %s" % \
            created_offer['engine_result'] if created_offer \
            else 'Offer was not created'
        logger.info(status_msg)
        return {'status': 'error',
                'status_msg': status_msg,
                'sold': 0,
                'bought': 0}

    logger.info("Offer created: %s" % created_offer)
    tr_hash = created_offer['tx_json']['hash']
    logger.info("Transaction: %s" % tr_hash)

    # check transaction result
    transaction = get_transaction_result(tr_hash, timeout, servers)

    # if trade didn't happen
    if 'AffectedNodes' not in transaction.get('meta', ''):
        status_msg = "Offer was not identified."
        logger.info("%s AffectedNodes weren't found." % status_msg)
        return {'status': 'error',
                'status_msg': status_msg,
                'sold': 0,
                'bought': 0}

    logger.info("Offer identified: looking for sold, received amount. \n %s" %
                transaction)
    sold, received = get_sold_received(transaction)
    logger.info("Amount sold: %s, Amount received: %s" %
                (sold, received))

    return {'status': 'success',
            'status_msg': 'Trade successfully happened',
            'sold': sold,
            'bought': received}


def get_transaction_result(tr_hash, timeout, servers, attempts=5, wait=2):
    """
    Get created offer hash and look for offer result after it's processing.

    takes:
        tr_hash  - str  - ripple transaction hash
        timeout  - int  - transaction timeout
        servers  - list - ripple servers
        attempts - int  - number of attempts to check if trade happened
        wait     - int  - seconds to wait until next check
    returns:
        transaction result if it's happened or None

    """
    transaction = {}

    # wait for ripple path find
    if not strtobool(os.environ.get("TESTING", "no")):
        time.sleep(wait)

    for i in xrange(attempts):
        transaction = tx(tr_hash, timeout=timeout, servers=servers)
        # check if offer happened
        if 'AffectedNodes' in transaction:
            break
        # wait for ripple path find a little more
        if not strtobool(os.environ.get("TESTING", "no")):
            time.sleep(wait)
    return transaction


def get_sold_received(transaction):
    """
    Calculate amount sold and amount bought from processed offer result.

    takes:
        transaction  -  dict  - ripple tx call result

    returns:
        pays_sum     -  float - amount sold
        gets_sum     -  float - amount bought

    """
    nodes = transaction['meta']['AffectedNodes']
    pays_sum = 0
    gets_sum = 0
    for n in nodes:

        if n.get('DeletedNode', ''):
            played = n['DeletedNode']
            if played.get('LedgerEntryType', '') == 'Offer':
                fields = played['PreviousFields']
                pays_curr, pays_val = restore_taker_values(fields['TakerPays'])
                gets_curr, gets_val = restore_taker_values(fields['TakerGets'])

                pays_sum += pays_val
                gets_sum += gets_val

        if n.get('ModifiedNode', ''):
            played = n['ModifiedNode']
            if played.get('LedgerEntryType', '') == 'Offer':
                prev_fields = played['PreviousFields']
                final_fields = played['FinalFields']
                pf_pays_curr, pf_pays_val = \
                    restore_taker_values(prev_fields['TakerPays'])
                pf_gets_curr, pf_gets_val = \
                    restore_taker_values(prev_fields['TakerGets'])
                ff_pays_currency, ff_pays_value = \
                    restore_taker_values(final_fields['TakerPays'])
                ff_gets_currency, ff_gets_amount = \
                    restore_taker_values(final_fields['TakerGets'])

                pays_sum += pf_pays_val - ff_pays_value
                gets_sum += pf_gets_val - ff_gets_amount

    return pays_sum, gets_sum


def restore_taker_values(taker):
    if isinstance(taker, dict):
        currency = taker['currency']
        value = Decimal(taker['value'])
    return currency, value


def sell_all_or_cancel(taker_pays, taker_gets,
                       account, secret,
                       timeout, fee=10000, servers=None):

    return create_offer(
        taker_pays, taker_gets, account, secret, timeout, fee,
        flags=0x00080000 | 0x00020000, servers=servers)


def create_offer(taker_pays, taker_gets,
                 account, secret,
                 timeout, fee=10000, flags=0, servers=None):
    """
    Create trading offer.

    takes:
        taker_pays -  {
            'value':    - float - amount to buy
            'currency': - str   - currency
            'issuer':   - str   - issuer
        }
        taker_gets -  {
            'value':    - float - amount to sell
            'currency': - str   - currency
            'issuer':   - str   - issuer
        }
        account    - ripple account
        secret     - ripple secret
        timeout    - trade timeout
        fee        - ripple fee (default: 10000)
        flags      - trade flags (default: 0)
        servers    - ripple servers (default: none)

    returns:
        offer

    taker - user, that accepts your offer

    """

    taker_pays = taker_pays.copy()
    taker_gets = taker_gets.copy()
    taker_pays['value'] = "%.12f" % taker_pays['value']
    taker_gets['value'] = "%.12f" % taker_gets['value']
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
    logger.info('Trade offer: %s' % offer)
    return call_api(offer, timeout=timeout, servers=servers)
