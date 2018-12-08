# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Transaction'
        db.create_table('ripple_api_transaction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('account', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('destination', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('hash', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('tx_blob', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('issuer', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('source_tag', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('destination_tag', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('ledger_index', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='returning_transaction', null=True, to=orm['ripple_api.Transaction'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('ripple_api', ['Transaction'])


    def backwards(self, orm):
        # Deleting model 'Transaction'
        db.delete_table('ripple_api_transaction')


    models = {
        'ripple_api.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'account': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'destination': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'destination_tag': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
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