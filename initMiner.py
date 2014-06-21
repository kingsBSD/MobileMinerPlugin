import ConfigParser
import json

import ckanapi
import pylons


def setup(config,log=False):
    
    ckan_url = config.get('settings', 'ckan_url').rstrip('/')
    api_key = config.get('settings', 'api_key')

    print api_key, ckan_url
    local = ckanapi.RemoteCKAN(ckan_url,apikey=api_key)

    existing = []
    existingResources = []

    if not log:
        data = dict([ (key,config.get('settings',key)) for key in ['name','title','notes'] ])
        package = local.action.package_create(**data)
        package_id = package['id']
        
        logfile = open('config.log','w')
        log = ConfigParser.SafeConfigParser()
        log.add_section('package')
        log.set('package','id',package_id)
        log.write(logfile)
        logfile.close()
          
    else:
        package_id = log.get('package','id')
        try:
            existing = log.get('package','tables').split(',')
            existingResources = log.get('package','resources').split(',')
        except:
            pass
    
    created = []
    tables = config.get('settings','tables').split(',')
    
    for table in tables:
        fieldNames = ['uid'] + config.get(table,'fields').split(',')
        fieldTypes = ['bigint'] + config.get(table,'field_types').split(',')
        fields = [ {'id':field[0], 'type':field[1]} for field in zip(fieldNames,fieldTypes) ]
        if table not in existing:
            created.append(local.action.datastore_create(resource={'package_id':package_id, 'name':table}, fields=fields))
        
#        versions = config.get(table,'api_versions').split(',')

#        for version in versions:
#            tableName = '_'.join([table,str(version)])
#            if tableName not in existing:
#                created.append(local.action.datastore_create(resource={'package_id':package_id, 'name':tableName}, fields=fields))
    
    newLogFile = open('/etc/ckan/default/mobileminer.log','w')
    newLog = ConfigParser.SafeConfigParser()
    newLog.add_section('package')
    newLog.set('package','id',package_id)
    newLog.set('package', 'tables', ','.join(existing + [ table['resource']['name'] for table in created ]))
    newLog.set('package', 'resources', ','.join(existingResources + [ table['resource_id'] for table in created ]))
    newLog.write(newLogFile)
    newLogFile.close()

#    apis = {}
#    for table in zip(existing + [ name['resource']['name'] for name in created ], existingResources + [ res['resource_id'] for res in created ]):
#        name,version = table[0].split('_')
#        if not apis.get(version,False):
#            apis[version] = {}
#        apis[version][name] = table[1]


#    for api in apis.keys():
#        apiFile = open('mobileminerapi'+api+'.json','w')
#        apiFile.write(json.dumps({'url':ckan_url, 'tables':apis[api]}))
#        apiFile.close()
        
if __name__ == '__main__':
    config = ConfigParser.SafeConfigParser()
    config.read('/etc/ckan/default/mobileminer.ini')
    
    log = ConfigParser.SafeConfigParser()
    try:
        log.read('/etc/ckan/default/mobileminer.log')
        package_id = log.get('package','id')
    except:
        log = False
    
    setup(config,log=log)
    
    
    
    