# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Transaction


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'destination',
                    'currency', 'value', 'ledger_index', 'status')

admin.site.register(Transaction, TransactionAdmin)
