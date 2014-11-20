# -*- coding: utf-8 -*-

# system:
from decimal import Decimal
import time
import logging

# Django:
# thirdparty:
from ripple_api.ripple_api import call_api, tx

# coinhand:
from django.conf import settings


logger = logging.getLogger('ripple_trade_offers')


def sell_all(buy_expected, sell_needed):
    """
    Exchange the entire sell needed amount, even if it means obtaining more
    than the buy expected amount in exchange.
    takes:
    buy_expected -  {
        'amount':   - float - min amount to buy
        'currency': - str   - currency
        'issuer':   - str   - issuer
    }
    buy_expected -  {
        'amount':   - float - amount to sell
        'currency': - str   - currency
        'issuer':   - str   - issuer
    }
    returns: {
        'status':      - str    - 'success' / 'error',
        'status_msg':  - str    - 'status description'
        'sold': 0,     - float  - the amount sold
        'bought': 0    - float  - the amount bought
    }
    """
    offer = sell_all_or_cancel(buy_expected, sell_needed)
    offer_result = get_trade_result(offer)
    offer_result['sell_amount_left'] = Decimal(
        "%.12f" % float(sell_needed['amount'] - offer_result['sold']))

    if offer_result['sold'] >= sell_needed['amount'] - settings.DEFAULT_PRECISION:
        logger.info("Trade fully funded")
    elif offer_result['sold']:
        logger.info("Trade partially happen")
    else:
        logger.info("Trade didn't happen")

    return offer_result


def get_trade_result(created_offer):
    """
    Gets created offer result and processes it to human readable format.
    takes:
        ripple offer result returned by CreateOffer call

    returns: {
        'status':      - str   - 'success' / 'error',
        'status_msg':  - str   - 'status description'
        'sold': 0,     - float - the amount sold
        'bought': 0    - float - the amount bought
    }
    """
    # check offer result
    if not created_offer or created_offer['engine_result'] != 'tesSUCCESS':
        creation_status = 'Offer was not created' if not created_offer else created_offer['engine_result']
        status_msg = "Offer creation failed: %s" % creation_status
        logger.info(status_msg)
        return {'status': 'error',
                'status_msg': status_msg,
                'sold': 0,
                'bought': 0}

    logger.info("Offer created: \n%s", created_offer)
    tr_hash = created_offer['tx_json']['hash']
    logger.info("Transaction: %s" % tr_hash)

    # check transaction result
    transaction = get_transaction_result(tr_hash)

    # if trade didn't happen
    if not 'AffectedNodes' in transaction.get('meta', ''):
        status_msg = "Offer was not identified."
        logger.info("%s AffectedNodes weren't found." % status_msg)
        return {'status': 'error',
                'status_msg': status_msg,
                'sold': 0,
                'bought': 0}

    logger.info("Offer identified: looking for sold, received amount. \n %s" % transaction)
    sold, received = get_sold_received(transaction)
    logger.info("Amount sold: %s, Amount received: %s" %
                (sold, received))

    return {'status': 'success',
            'status_msg': 'Trade successfully happened',
            'sold': sold,
            'bought': received}


def get_transaction_result(tr_hash, attempts=5, wait=2):
    """
    Gets created offer hash and looks for offer result after it's processing.
    takes:
        tr_hash  - str - ripple transaction hash
        attempts - int - number of attempts to check if trade happened
        wait     - int - seconds to wait until next check
    returns:
        transaction result if it's happened or None
    """
    transaction = {}

    # wait for ripple path find
    if not settings.TESTING:
        time.sleep(5)

    for i in xrange(attempts):
        transaction = tx(tr_hash, timeout=settings.RIPPLE_TIMEOUT)
        # check if offer happened
        if 'AffectedNodes' in transaction:
            break
        # wait for ripple path find a little more
        time.sleep(wait)
    return transaction


def get_sold_received(transaction):
    """
    Calculates amount sold and amount bought from processed offer result.
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
                pf_pays_curr, pf_pays_val = restore_taker_values(prev_fields['TakerPays'])
                pf_gets_curr, pf_gets_val = restore_taker_values(prev_fields['TakerGets'])
                ff_pays_currency, ff_pays_value = restore_taker_values(final_fields['TakerPays'])
                ff_gets_currency, ff_gets_amount = restore_taker_values(final_fields['TakerGets'])

                pays_sum += pf_pays_val - ff_pays_value
                gets_sum += pf_gets_val - ff_gets_amount

    return pays_sum, gets_sum


def restore_taker_values(taker):
    if isinstance(taker, dict):
        currency = taker['currency']
        value = Decimal(taker['value'])
    return currency, value


def sell_all_or_cancel(taker_pays, taker_gets,
                       account=settings.RIPPLE_ACCOUNT,
                       secret=settings.RIPPLE_SECRET,
                       timeout=settings.RIPPLE_TIMEOUT,
                       fee=10000):

    return create_offer(
        taker_pays, taker_gets, account, secret, timeout, fee,
        flags=0x00080000 | 0x00020000)


def create_offer(taker_pays, taker_gets,
                 account=settings.RIPPLE_ACCOUNT,
                 secret=settings.RIPPLE_SECRET,
                 timeout=settings.RIPPLE_TIMEOUT,
                 fee=10000, flags=0):
    """
    taker - user, that accepts your offer
    takes:
        taker_pays -  {
            'amount':   - float - amount to buy
            'currency': - str   - currency
            'issuer':   - str   - issuer
        }
        taker_gets -  {
            'amount':   - float - amount to sell
            'currency': - str   - currency
            'issuer':   - str   - issuer
        }
    """

    taker_pays['amount'] = "%.12f" % taker_pays['amount']
    taker_gets['amount'] = "%.12f" % taker_gets['amount']
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
