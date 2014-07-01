# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'counters'
        db.create_table('tldap_counters', (
            ('id', self.gf('django.db.models.fields.AutoField')
                (primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')
                (max_length=20, db_index=True)),
            ('count', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('methods', ['counters'])

    def backwards(self, orm):
        # Deleting model 'counters'
        db.delete_table('tldap_counters')

    models = {
        'methods.counters': {
            'Meta': {
                'object_name': 'counters', 'db_table': "'tldap_counters'"},
            'count': ('django.db.models.fields.IntegerField', [], {}),
            'id': (
                'django.db.models.fields.AutoField',
                [], {'primary_key': 'True'}),
            'name': (
                'django.db.models.fields.CharField',
                [], {'max_length': '20', 'db_index': 'True'})
        }
    }

    complete_apps = ['methods']
