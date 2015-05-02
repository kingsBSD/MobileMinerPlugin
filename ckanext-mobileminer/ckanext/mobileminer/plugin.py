# Licensed under the Apache License Version 2.0: http://www.apache.org/licenses/LICENSE-2.0.txt

__author__ = 'Giles Richard Greenway'

import base
import ckanapi
import ckan.plugins as plugins
import ckanext.datastore.db as db

import ConfigParser
import datetime
import json
import random

config = ConfigParser.SafeConfigParser()
config.read('/etc/ckan/default/mobileminer.ini')

ckan_url = config.get('settings', 'ckan_url').rstrip('/')
api_key = config.get('settings', 'api_key')

#log = ConfigParser.SafeConfigParser()
#log.read('/etc/ckan/default/mobileminer.log')
#resources = dict(zip(log.get('package','tables').split(','), log.get('package','resources').split(',')))

resources = base.get_resources()

@plugins.toolkit.auth_allow_anonymous_access
def miner_auth_update(context, data_dict=None):
    return {'success': True, 'msg': "Yes you can."}

@plugins.toolkit.auth_allow_anonymous_access
def miner_auth_register(context, data_dict=None):
    return {'success': True, 'msg': "Yes you can."}

def user_exists(uid):
    local = ckanapi.RemoteCKAN(ckan_url,apikey=api_key) 
    userResource = resources.get('user')
    userExists = len(local.action.datastore_search(resource_id=userResource, filters={'uid':uid}, limit=1)['records'])
    return userExists >= 1

# curl http://localhost:5000/api/action/miner_update -d '{"uid":281753793, "table":"minerlog", "records":[{"start":"2014-05-12T17:55:54","stop":"2014-05-13T17:55:54"}]}'

@plugins.toolkit.side_effect_free
def miner_datastore_update(context,data):
    
    uid = data.get('uid',False)    
    if not uid:
        raise plugins.toolkit.ValidationError({'message': 'No uid specified.'})
    
    local = ckanapi.RemoteCKAN(ckan_url,apikey=api_key) 
    
    userResource = resources.get('user')
    userExists = len(local.action.datastore_search(resource_id=userResource, filters={'uid':uid}, limit=1)['records'])
    
    if userExists == 0:
        raise plugins.toolkit.ValidationError({'message': 'No such user.'})
        
    
    table = data.get('table',False)
    if not table:
        raise plugins.toolkit.ValidationError({'message': 'No table specified.'})
    if not table in config.get('settings','tables').split(',') or table == 'user':
        raise plugins.toolkit.ValidationError({'message': 'Invalid table: '+table})
    fields = config.get(table,'fields').split(',')
    fieldSet = set(fields)
    records = data.get('records',False)
    if not records:
        raise plugins.toolkit.ValidationError({'message': 'No records specified.'})
    
    for record in records:
        record['uid'] = uid
        missing = list(fieldSet.difference(set(record.keys())))
        if missing:
            raise plugins.toolkit.ValidationError({'message': 'missing fields: '+' '.join(missing)})
 
    result = local.action.datastore_upsert(resource_id=resources[table],records=records,method='insert')
        
    return len(records)

@plugins.toolkit.side_effect_free
def miner_datastore_register(context,data):
    missing = [ field for field in ['androidid','version'] if not data.get(field,False) ]
    if missing:
        raise plugins.toolkit.ValidationError({'message': 'Not specified: '+', '.join(missing)})
    
    newUser = False
    while not newUser:
        uid = abs(random.getrandbits(32))
        newUser = not user_exists(uid)
        
    local = ckanapi.RemoteCKAN(ckan_url,apikey=api_key)         
    result = local.action.datastore_upsert(resource_id=resources['user'],
        records=[{'uid':uid, 'androidid':data['androidid'], 'version':data['version'], 'time':datetime.datetime.now().isoformat()}],
        method='insert')
    
    return uid

class MobileMinerPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IActions)

    def get_auth_functions(self):
        return {'miner_update': miner_auth_update, 'miner_register':miner_auth_register}
    
    def get_actions(self):
        return {'miner_update': miner_datastore_update, 'miner_register':miner_datastore_register}
