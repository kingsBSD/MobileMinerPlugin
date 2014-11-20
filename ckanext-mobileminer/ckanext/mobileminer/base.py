import ckanapi
#import ckan.plugins as plugins
#import ckanext.datastore.db as db

import ConfigParser
#import datetime
#import json
#import random

def get_config():
    config = ConfigParser.SafeConfigParser()
    config.read('/etc/ckan/default/mobileminer.ini')
    return config

weekdays = dict(zip(range(1,8),['Mon','Tue','Wed','Thu','Fri','Sat','Sun']))
    
def get_local():
    config = get_config()
    ckan_url = config.get('settings', 'ckan_url').rstrip('/')
    api_key = config.get('settings', 'api_key')
    
    return ckanapi.RemoteCKAN(ckan_url,apikey=api_key)     
    
def get_resources():
    config = get_config()
    try:
        return dict(zip(config.get('generated','tables').split(','),config.get('generated','resources').split(',')))
    except:
        return {}
    
def get_package_id():
    config = get_config()
    try:
        return config.get('generated','package_id')
    except:
        return False

def get_field_types():
    config = get_config()
    tables = config.get('settings','tables').split(',') + config.get('settings','non_user_tables').split(',')
    return dict([(table, dict(zip(config.get(table,'fields').split(','),config.get(table,'field_types').split(',')))) for table in tables ])

    
    