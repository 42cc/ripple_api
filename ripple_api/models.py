# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import ModelTracker

from signals import transaction_status_changed, transaction_failure_send


class Transaction(models.Model):
    RECEIVED = 0
    PROCESSED = 1
    MUST_BE_RETURN = 2
    RETURNING = 3
    RETURNED = 4
    PENDING = 5
    SUBMITTED = 6
    FAILURE = 7
    SUCCESS = 8
    CREATED = 9
    SUCCESS_PROCESSED = 10
    FAIL_FIXED = 100

    STATUS_CHOICES = (
        (RECEIVED, _(u'Transaction received')),
        (PROCESSED, _(u'Transaction was processed')),
        (MUST_BE_RETURN, _(u'This transaction must be returned to user')),
        (RETURNING, _(u'Created new transaction for returning')),
        (RETURNED, _(u'Transaction was returned')),
        (PENDING, _(u'Pending to submit')),
        (SUBMITTED, _(u'Transaction was submitted')),
        (FAILURE, _(u'Transaction was failed')),
        (SUCCESS, _(u'Transaction was completed successfully')),
        (CREATED, _(u'Transaction was created but not sign')),
        (SUCCESS_PROCESSED,
            _(u'Transaction was processed after successful submit')),
        (FAIL_FIXED, _(u'The failed transaction was fixed by a new retry'))
    )

    account = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    hash = models.CharField(max_length=100, blank=True)
    tx_blob = models.TextField(blank=True)

    currency = models.CharField(max_length=3)
    issuer = models.CharField(max_length=100)
    value = models.CharField(max_length=100)

    source_tag = models.IntegerField(null=True, blank=True)
    destination_tag = models.IntegerField(null=True, blank=True)
    ledger_index = models.IntegerField(null=True, blank=True)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=RECEIVED)

    parent = models.ForeignKey('self', null=True, blank=True,
                               related_name='returning_transaction')
    created = models.DateTimeField(auto_now_add=True)

    status_tracker = ModelTracker(fields=['status'])

    def __unicode__(self):
        return u'[%s] %s. %s %s from %s to %s' % (
            self.pk, self.created, self.value,
            self.currency, self.account, self.destination
        )

    def save(self, *args, **kwargs):
        created = bool(self.pk)
        super(Transaction, self).save(*args, **kwargs)

        if created and self.status_tracker.previous('status') is not None:
            transaction_status_changed.send(
                sender=self.__class__,
                instance=self,
                old_status=self.status_tracker.previous('status')
            )
        if self.status == self.FAILURE:
            transaction_failure_send.send(sender=self.__class__, instance=self)
