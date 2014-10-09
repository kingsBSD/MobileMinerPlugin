from paste.script.command import Command
import ckanapi
import ConfigParser

class MinerCommands(Command):
    summary = "--NO SUMMARY--"
    usage = "--NO USAGE--"
    parser = Command.standard_parser(verbose=False)
    config = ConfigParser.SafeConfigParser()
    local = False
    #local = ckanapi.LocalCKAN(username='admin')

    def command(self):
        self.config.read('/etc/ckan/default/mobileminer.ini')
        
        ckan_url = self.config.get('settings', 'ckan_url').rstrip('/')
        api_key = self.config.get('settings', 'api_key')
        self.local = ckanapi.RemoteCKAN(ckan_url,apikey=api_key)
        
        action = self.args[0]
        
        if action == 'minertables':
            self.minertables()
            
    def minertables(self):
        
        log = ConfigParser.SafeConfigParser()
        try:
            log.read('/etc/ckan/default/mobileminer.log')
            package_id = log.get('package','id')
        except:
            log = False

        existing = []
        existingResources = []
        
        if not log:
            data = dict([ (key,self.config.get('settings',key)) for key in ['name','title','notes'] ])
            package = self.local.action.package_create(**data)
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
        tables = self.config.get('settings','tables').split(',')
    
        for table in tables:
            fieldNames = ['uid'] + self.config.get(table,'fields').split(',')
            fieldTypes = ['bigint'] + self.config.get(table,'field_types').split(',')
            fields = [ {'id':field[0], 'type':field[1]} for field in zip(fieldNames,fieldTypes) ]
            if table not in existing:
                print "Creating table: "+table
                created.append(self.local.action.datastore_create(resource={'package_id':package_id, 'name':table}, fields=fields))
                
        
        newLogFile = open('/etc/ckan/default/mobileminer.log','w')
        newLog = ConfigParser.SafeConfigParser()
        newLog.add_section('package')
        newLog.set('package','id',package_id)
        newLog.set('package', 'tables', ','.join(existing + [ table['resource']['name'] for table in created ]))
        newLog.set('package', 'resources', ','.join(existingResources + [ table['resource_id'] for table in created ]))
        newLog.write(newLogFile)
        newLogFile.close()

        

