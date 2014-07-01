# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Counters.scheme'
        db.add_column('tldap_counters', 'scheme',
                      self.gf('django.db.models.fields.CharField')
                      (default='default', max_length=20, db_index=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Counters.scheme'
        db.delete_column('tldap_counters', 'scheme')

    models = {
        'methods.counters': {
            'Meta': {
                'object_name': 'Counters', 'db_table': "'tldap_counters'"},
            'count': ('django.db.models.fields.IntegerField', [], {}),
            'id': (
                'django.db.models.fields.AutoField',
                [], {'primary_key': 'True'}),
            'name': (
                'django.db.models.fields.CharField',
                [], {'max_length': '20', 'db_index': 'True'}),
            'scheme': (
                'django.db.models.fields.CharField',
                [], {'max_length': '20', 'db_index': 'True'})
        }
    }

    complete_apps = ['methods']
