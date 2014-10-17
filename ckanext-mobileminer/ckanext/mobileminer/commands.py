from paste.script.command import Command
import ckanapi
import ConfigParser
import uuid
import csv
import sys
from datetime import datetime
from ckan.lib.celery_app import celery
import base
from db import select, all_the_mnc

class MinerCommands(Command):
    summary = "--NO SUMMARY--"
    usage = "--NO USAGE--"
    parser = Command.standard_parser(verbose=False)
    config = ConfigParser.SafeConfigParser()
    local = False

    def command(self):
        self.config.read('/etc/ckan/default/mobileminer.ini')
        
        ckan_url = self.config.get('settings', 'ckan_url').rstrip('/')
        api_key = self.config.get('settings', 'api_key')
        self.local = ckanapi.RemoteCKAN(ckan_url,apikey=api_key)
        
        action = self.args[0]
        
        if action == 'minertables':
            self.minertables()

        if action == 'gsmupdate':
            celery.send_task("NAME.gsmupdate", task_id=str(uuid.uuid4()))

        if action == 'dailyusageupdate':
            celery.send_task("NAME.dailyusageupdate", task_id=str(uuid.uuid4()))
            
        if action == 'task':
            self.do_task()

        if action == 'push':
            self.push()

        if action == 'pushcells':
            self.push_cells()
          
            
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
        non_user_tables = self.config.get('settings','non_user_tables').split(',')
    
        for table in tables + non_user_tables:
            if table not in non_user_tables:
                fieldNames = ['uid'] + self.config.get(table,'fields').split(',')
                fieldTypes = ['bigint'] + self.config.get(table,'field_types').split(',')
            else:
                fieldNames = self.config.get(table,'fields').split(',')
                fieldTypes = self.config.get(table,'field_types').split(',')
                
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

    def push(self):

        if len(self.args) >= 3:
            table = self.args[1]
            fname = self.args[2]
        else:
            print "USAGE: push <table> <csvfile>"
            return

        res = base.get_resources().get(table,False)
        
        if not res:
            print "No such table: "+table
            return
        
        non_user_tables = self.config.get('settings','non_user_tables').split(',')
        if table not in non_user_tables:
            fields = ['uid'] + self.config.get(table,'fields').split(',')
        else:
            fields = self.config.get(table,'fields').split(',')
        
        try:
            infile = open(fname,'rb')
        except:
            print "Cant't open "+fname

        local = base.get_local()
        
        reader = csv.reader(infile, delimiter=',')
        reader.next()
        data = []
        for row in reader:
            data.append(dict(zip(fields,row[1:])))
            if len(data) == 50:
                local.action.datastore_upsert(resource_id=res,records=data,method='insert')
                sys.stdout.write('.')
                data = []
        if len(data):
            local.action.datastore_upsert(resource_id=res,records=data,method='insert')
            
    def do_task(self):
        celery.send_task("NAME."+self.args[1], task_id=str(uuid.uuid4()))
                        
    def push_cells(self):
        try:
            cell_file = open(self.args[1],'rb')
        except:
            return
        
        local = base.get_local()
        resources = base.get_resources()
        timestamp = datetime.now().isoformat()
        
        all_the_mcc = [ record['mcc'] for record in local.action.datastore_search_sql(sql=select(['mcc'],'gsmcell',ne={'mcc':'None'}))['records'] ]
        
        mnc_map = dict([ (mcc,all_the_mnc(mcc)) for mcc in all_the_mcc ])
                
        #print all_the_mcc
        #print all_the_mnc
        
        tick = 0
        found = 0
        sfound = '0'
        last_mcc = 0
        last_mnc = 0
        smcc = '0'
        smnc = '0'
        
        for line in cell_file.readlines():
            if line.split(',')[0] == 'radio':
                idx = {'mcc':1, 'mnc':2, 'lac':3, 'cid':4, 'lon':6, 'lat':7, 'changeable':10 }
                change = lambda x: x
            else:
                idx = {'mcc':0, 'mnc':1, 'lac':2, 'cid':3, 'lon':4, 'lat':5, 'changeable':7 }
                change = lambda x: 1 if x else 0
            break
        cell_file.close()
                
        cell_file = open(self.args[1],'rb')
        for line in cell_file.readlines():
            if tick % 256 == 0:
                print "Searching. MCC:" + smcc + " MNC:" + smnc + " Found: "+sfound
                tick = 1
            else:
                tick += 1
            chunks = line.split(',')
            #print chunks
            if len(chunks) < 11:
                continue
            
            mcc = chunks[idx['mcc']]
            mnc = chunks[idx['mnc']]
            
            if last_mcc <> mcc:
                smcc = str(mcc)
            if last_mnc <> mnc:
                smnc = str(mnc)    
            if mcc in all_the_mcc:
                if mnc in mnc_map[mcc]:
                    lac = chunks[idx['lac']]
                    cid = chunks[idx['cid']]
                    eq = {'mcc':mcc,'mnc':mnc,'lac':lac,'cid':cid}
                    ex_query = 'cid NOT IN (' + select(['cid::text'],'gsmlocation',eq=eq) + ')'
                    sql_query = select(['cid'],'gsmcell',eq=eq,where=ex_query)
                    insert = len(local.action.datastore_search_sql(sql=sql_query)['records']) > 0
                    if insert:
                        found += 1
                        sfound = str(found)
                        rendered_cell = {'mcc':mcc, 'mnc':mnc, 'lac':lac, 'cid':cid, 'lat':chunks[idx['lat']], 'lon':chunks[idx['lon']],
                            'changeable':change(chunks[idx['changeable']]), 'retrieved':timestamp}
                        print "Found: "+','.join([ rendered_cell[f] for f in ['mcc','mnc','lac','cid'] ])
                        local.action.datastore_upsert(resource_id=resources['gsmlocation'],records=[rendered_cell],method='insert')
            last_mcc = mcc
            last_mnc = mnc
                    
                    

           
            
            
        
