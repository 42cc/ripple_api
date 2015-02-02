# -*- coding: utf-8 -*-

from requests.exceptions import ConnectionError
import logging
import datetime

#from ...conf import RIPPLE_ACCOUNT, RIPPLE_SECRET
from django.conf import settings
from django.core.management.base import NoArgsCommand

from ripple_api.ripple_api import account_tx, tx, RippleApiError
from ripple_api.models import Transaction
from ripple_api.tasks import sign_task, submit_task


MAX_RESULTS = 200


def get_min_ledger_index():
    transactions = Transaction.objects.filter(status__in=[
            Transaction.RECEIVED, Transaction.PROCESSED,
            Transaction.MUST_BE_RETURN, Transaction.RETURNING,
            Transaction.RETURNED
            ]).order_by('-pk')
    return transactions[0].ledger_index if transactions else -1


class Command(NoArgsCommand):
    help = 'Command that processes transactions.'
    logger = logging.getLogger('ripple')
    logger.setLevel(40)

    def format_log_message(self, message, transaction=None, *args):
        if transaction or args:
            format_args = [transaction]
            format_args.extend(args)
            return message % tuple(format_args)
        else:
            return message

    def handle_noargs(self, **options):
        self.retry_failed_transactions()
        self.monitor_transactions()
        self.return_funds()
        self.submit_pending_transactions()
        self.check_submitted_transactions()

    def monitor_transactions(self):
        """
        Get new transactions for settings.RIPPLE_ACCOUNT and store them in DB

        """
        start_time = datetime.datetime.now()
        self.logger.info(self.format_log_message(
                'Looking for new ripple transactions since last run'))
        ledger_min_index = get_min_ledger_index()
        marker = None
        has_results = True
        try: timeout = settings.RIPPLE_TIMEOUT
        except AttributeError: timeout = 5

        while has_results:
            try:
                response = account_tx(settings.RIPPLE_ACCOUNT,
                                      ledger_min_index, limit=200,
                                      marker=marker,
                                      timeout=timeout)
                # self.logger.info(self.format_log_message(response))
            except (RippleApiError, ConnectionError), e:
                self.logger.error(self.format_log_message(e))
                break

            transactions = response['transactions']
            marker = response.get('marker')
            has_results = bool(marker)

            for transaction in transactions:
                tr_tx = transaction['tx']
                meta = transaction.get('meta', {})
                if meta.get('TransactionResult') != 'tesSUCCESS':
                    continue
                amount = meta.get('delivered_amount') or tr_tx.get('Amount', {})

                unprocessed_unstored_transactions = (
                    tr_tx['TransactionType'] == 'Payment' and
                    tr_tx['Destination'] == settings.RIPPLE_ACCOUNT and
                    isinstance(amount, dict) and
                    not Transaction.objects.filter(hash=tr_tx['hash'])
                )
                if unprocessed_unstored_transactions:
                        self.logger.info(self.format_log_message('Saving transaction: %s', transaction))
                        destination_tag = tr_tx.get('DestinationTag')
                        source_tag = tr_tx.get('SourceTag')

                        transaction_object = Transaction.objects.create(
                            account=tr_tx['Account'], hash=tr_tx['hash'],
                            destination=settings.RIPPLE_ACCOUNT,
                            ledger_index=tr_tx['ledger_index'],
                            destination_tag=destination_tag,
                            source_tag=source_tag, status=Transaction.RECEIVED,
                            currency=amount['currency'],
                            issuer=amount['issuer'], value=amount['value']
                        )
                        self.logger.info(self.format_log_message(
                                "Transaction saved: %s", transaction_object))
            if (datetime.datetime.now() - start_time
                >= datetime.timedelta(seconds=270) and has_results):
                has_results = False
                self.logger.error(
                    'Process_transactions command terminated because '
                    '(270 seconds) timeout: ' + unicode(marker))

    def check_submitted_transactions(self):
        """
        Check final disposition of transactions.
        """
        self.logger.info(self.format_log_message('Checking submitted transactions'))
        for transaction in Transaction.objects.filter(status=Transaction.SUBMITTED):
            try:
                response = tx(transaction.hash)
                self.logger.info(self.format_log_message(response))
            except RippleApiError as e:
                self.logger.error(self.format_log_message("Error processing %s: %s", transaction, e))
                if e.error == 'txnNotFound':
                    self.logger.info(self.format_log_message(
                        'Setting transaction status to Failed for %s', transaction
                    ))
                    transaction.status = Transaction.FAILURE
                    transaction.save()
                continue

            status = response.get('meta', {}).get('TransactionResult')

            if status == 'tesSUCCESS':
                transaction.status = Transaction.SUCCESS
                transaction.save()

                if transaction.parent:
                    transaction.parent.status = Transaction.RETURNED
                    transaction.parent.save()

                self.logger.info(self.format_log_message(
                    "Transaction: %s to %s was complete.", transaction, transaction.destination
                    )
                )
            else:
                self.logger.info("Transaction status: %s" % status)

    def submit_pending_transactions(self):
        """
        Submit transactions that was signed, but connection error occurred when submit it.
        """
        self.logger.info(self.format_log_message('Submit pending transactions'))
        for transaction in Transaction.objects.filter(status=Transaction.PENDING):
            self.logger.info(self.format_log_message('Submit: %s', transaction))
            submit_task.apply((transaction,))

    def return_funds(self):
        self.logger.info('Returning failed stakes')
        for transaction in Transaction.objects.filter(
                status=Transaction.MUST_BE_RETURN):
            self.logger.info("Transaction %s must be return." % transaction.pk)

            ret_transaction = Transaction.objects.create(
                account=settings.RIPPLE_ACCOUNT,
                destination=transaction.account,
                currency=transaction.currency,
                value=transaction.value,
                status=Transaction.PENDING,
                parent=transaction
            )
            sign_task.apply((ret_transaction, settings.RIPPLE_SECRET))
            transaction.status = Transaction.RETURNING
            transaction.save()
            self.logger.info("New transaction created for returning %s", ret_transaction.pk)

    def retry_failed_transactions(self):
        self.logger.info('Retrying failed transactions')
        for transaction in Transaction.objects.filter(
                status=Transaction.FAILURE):
            self.logger.info(self.format_log_message('Found %s', transaction))

            retry_transaction = Transaction.objects.create(
                account=transaction.account,
                destination=transaction.destination,
                currency=transaction.currency,
                value=transaction.value,
                status=Transaction.PENDING,
                parent=transaction.parent
            )
            sign_task.apply((retry_transaction, settings.RIPPLE_SECRET))
            self.logger.info("New transaction created for returning %s", retry_transaction.pk)
            transaction.status = Transaction.FAIL_FIXED
            transaction.save()
            self.logger.info("Fixed the transaction")
