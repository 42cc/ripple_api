# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    operations = (
        migrations.CreateModel(
            name='Transaction',
            fields=(
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account', models.CharField(max_length=100)),
                ('destination', models.CharField(max_length=100)),
                ('hash', models.CharField(blank=True, max_length=100)),
                ('tx_blob', models.TextField(blank=True)),
                ('currency', models.CharField(max_length=3)),
                ('issuer', models.CharField(max_length=100)),
                ('value', models.CharField(max_length=100)),
                ('source_tag', models.IntegerField(blank=True, null=True)),
                ('destination_tag', models.IntegerField(blank=True, null=True)),
                ('ledger_index', models.IntegerField(blank=True, null=True)),
                ('status', models.SmallIntegerField(choices=[(0, 'Transaction received'), (1, 'Transaction was processed'), (2, 'This transaction must be returned to user'), (3, 'Created new transaction for returning'), (4, 'Transaction was returned'), (5, 'Pending to submit'), (6, 'Transaction was submitted'), (7, 'Transaction was failed'), (8, 'Transaction was completed successfully'), (9, 'Transaction was created but not sign'), (10, 'Transaction was processed after successful submit'), (100, 'The failed transaction was fixed by a new retry')], default=0)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='returning_transaction', to='ripple_api.Transaction')),
            ),
        ),
    )
