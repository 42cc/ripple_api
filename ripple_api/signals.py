# -*- coding: utf-8 -*-
import django.dispatch

transaction_status_changed = django.dispatch.Signal(providing_args=["instance", "old_status"])
"""Signal that is fired after transaction status is changed"""

transaction_failure_send = django.dispatch.Signal(providing_args=["instance"])
"""Send signal when transaction is fail"""
