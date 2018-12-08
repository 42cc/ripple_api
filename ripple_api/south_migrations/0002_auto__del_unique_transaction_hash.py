# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Transaction', fields ['hash']
        db.delete_unique('ripple_api_transaction', ['hash'])


    def backwards(self, orm):
        # Adding unique constraint on 'Transaction', fields ['hash']
        db.create_unique('ripple_api_transaction', ['hash'])


    models = {
        'ripple_api.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'account': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'destination': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'destination_tag': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issuer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ledger_index': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'returning_transaction'", 'null': 'True', 'to': "orm['ripple_api.Transaction']"}),
            'source_tag': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'tx_blob': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['ripple_api']