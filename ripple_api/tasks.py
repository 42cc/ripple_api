# -*- coding: utf-8 -*-
from requests import ConnectionError
from celery import task
import logging
import time

from .models import Transaction
from ripple_api import RippleApiError, sign, submit, tx


@task
def sign_task(transaction, secret):
    logger = logging.getLogger('ripple')

    if transaction.currency == 'XRP':
        amount = transaction.value
    else:
        amount = {"currency": transaction.currency, "value": str(transaction.value), "issuer": transaction.issuer}

    try:
        response = sign(transaction.account, secret, transaction.destination, amount)
    except (RippleApiError, ConnectionError), e:
        transaction.status = Transaction.FAILURE
        transaction.save()
        logger.error(e)
        return

    transaction.hash = response['tx_json']['hash']
    transaction.tx_blob = response['tx_blob']
    transaction.status = Transaction.PENDING
    transaction.save()

    logger.info('Transaction signed: %s' % transaction)
    return transaction


@task
def submit_task(transaction):
    if transaction:
        logger = logging.getLogger('ripple')
        try:
            response = submit(transaction.tx_blob)
            if response['engine_result'] == "telINSUF_FEE_P":
                # ripple server too busy to forward or process your transaction
                while True:
                    time.sleep(2)
                    tx_response = tx(transaction.hash)
                    status = tx_response.get('meta', {}).get('TransactionResult')
                    # check if tx status is available
                    if status:
                        response['engine_result'] = status
                        break

        except RippleApiError, e:
            logger.error(e)
            transaction.status = Transaction.FAILURE
            transaction.save()
            return
        except ConnectionError, e:
            logger.error('Connection error: %s' % e)
            return

        if response['engine_result'] in ["tesSUCCESS",  "tefPAST_SEQ"]:
            transaction.status = Transaction.SUBMITTED
            transaction.save()
            logger.info("Transaction: %s successful submitted." % transaction)
        else:
            transaction.status = Transaction.FAILURE
            transaction.save()
            logger.info("Transaction: %s submitted with result %s" % (transaction, response['engine_result']))
