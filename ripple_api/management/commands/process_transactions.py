# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.core.management.base import NoArgsCommand

from ripple_api.ripple_api import tx, RippleApiError
from ripple_api.models import Transaction
from ripple_api.tasks import sign_task, submit_task
from ripple_api.management.transaction_processors import (
    monitor_transactions,
    format_log_message
)


MAX_RESULTS = 200


class Command(NoArgsCommand):
    help = 'Command that processes transactions.'
    logger = logging.getLogger('ripple')
    logger.setLevel(40)

    def handle_noargs(self, **options):
        self.retry_failed_transactions()
        monitor_transactions(account=settings.RIPPLE_ACCOUNT,
                             logger=self.logger)
        self.return_funds()
        self.submit_pending_transactions()
        self.check_submitted_transactions()

    def check_submitted_transactions(self):
        """
        Check final disposition of transactions.
        """
        self.logger.info(
            format_log_message(
                'Checking submitted transactions'
            )
        )

        submitted_transactions = Transaction.objects.filter(
            status=Transaction.SUBMITTED
        )
        for transaction in submitted_transactions:
            try:
                response = tx(transaction.hash)
                self.logger.info(format_log_message(response))
            except RippleApiError as e:
                self.logger.error(
                    format_log_message(
                        "Error processing %s: %s", transaction, e
                    )
                )
                if e.error == 'txnNotFound':
                    self.logger.info(
                        format_log_message(
                            'Setting transaction status to Failed for %s',
                            transaction
                        )
                    )
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

                self.logger.info(format_log_message(
                        "Transaction: %s to %s was complete.",
                        transaction, transaction.destination
                    )
                )
            else:
                self.logger.info("Transaction status: %s" % status)

    def submit_pending_transactions(self):
        """
        Submit transactions that was signed, but connection error occurred
        when submit it.
        """
        self.logger.info(format_log_message('Submit pending transactions'))
        pending_transactions = Transaction.objects.filter(
            status=Transaction.PENDING
        )
        for transaction in pending_transactions:
            self.logger.info(format_log_message('Submit: %s', transaction))
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
            self.logger.info(
                "New transaction created for returning %s", ret_transaction.pk
            )

    def retry_failed_transactions(self):
        self.logger.info('Retrying failed transactions')
        failed_transactions = Transaction.objects.filter(
            status=Transaction.FAILURE
        )
        for transaction in failed_transactions:
            self.logger.info(format_log_message('Found %s', transaction))

            retry_transaction = Transaction.objects.create(
                account=transaction.account,
                destination=transaction.destination,
                currency=transaction.currency,
                value=transaction.value,
                status=Transaction.PENDING,
                parent=transaction.parent
            )
            sign_task.apply((retry_transaction, settings.RIPPLE_SECRET))
            self.logger.info(
                "New transaction created for returning %s",
                retry_transaction.pk
            )
            transaction.status = Transaction.FAIL_FIXED
            transaction.save()
            self.logger.info("Fixed the transaction")
