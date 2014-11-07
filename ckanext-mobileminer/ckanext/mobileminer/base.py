import ckanapi
#import ckan.plugins as plugins
#import ckanext.datastore.db as db

import ConfigParser
#import datetime
#import json
#import random

config = ConfigParser.SafeConfigParser()
config.read('/etc/ckan/default/mobileminer.ini')
ckan_url = config.get('settings', 'ckan_url').rstrip('/')
api_key = config.get('settings', 'api_key')

tables = config.get('settings','tables').split(',') + config.get('settings','non_user_tables').split(',')

table_field_types = dict([ (table,dict(zip(config.get(table,'fields').split(','),config.get(table,'field_types').split(',')))) for table in tables ])

weekdays = dict(zip(range(1,8),['Mon','Tue','Wed','Thu','Fri','Sat','Sun']))
    
def get_local():
    return ckanapi.RemoteCKAN(ckan_url,apikey=api_key)     
    
def get_resources():
    local = get_local()
    try:
        return dict([ (r['name'],r['id']) for r in local.action.package_show(id='mobileminer')['resources'] ])
    except:
        return {}
    
def get_package_id():
    local = get_local()
    return local.action.package_show(id='mobileminer')['id']



    
    