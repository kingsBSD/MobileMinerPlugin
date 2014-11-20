from paste.script.command import Command
import ckanapi
import ConfigParser
import uuid
import csv
import sys
from datetime import datetime
import ConfigParser
import base
from db import select, all_the_mnc, get_users


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
        
        if action == 'init':
            self.init()
        
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
            
        if action == 'gsmtest':
            self.gsm_test()
            
        if action == 'flush':
            self.flush()     
    
    def push_settings(self,key,value):
        new_config = ConfigParser.SafeConfigParser()
        new_config.read('/etc/ckan/default/mobileminer.ini')
        new_config.set('generated',key,value)
        with open('/etc/ckan/default/mobileminer.ini', 'wb') as configfile:
            new_config.write(configfile)
    
    def init(self):
        pars = dict([ (key,self.config.get('settings',key)) for key in ['name','title','notes'] ])
        package_id = self.local.action.package_create(**pars)['id']
        self.push_settings('package_id',package_id)
        self.minertables()
    
    def minertables(self):
        resources = base.get_resources()
        existing = resources.keys()
        package_id = base.get_package_id()

        new_fields = []

        tables = self.config.get('settings','tables').split(',')
        non_user_tables = self.config.get('settings','non_user_tables').split(',')
    
        for table in tables + non_user_tables:
            
            if table in existing:
                continue
            
            if table not in non_user_tables:
                fieldNames = ['uid'] + self.config.get(table,'fields').split(',')
                fieldTypes = ['bigint'] + self.config.get(table,'field_types').split(',')
            else:
                fieldNames = self.config.get(table,'fields').split(',')
                fieldTypes = self.config.get(table,'field_types').split(',')
                
            fields = [ {'id':field[0], 'type':field[1]} for field in zip(fieldNames,fieldTypes) ]
            print "Creating table: "+table
            new_fields.append(self.local.action.datastore_create(resource={'package_id':package_id, 'name':table }, fields=fields))
            
        tables = existing + [ table['resource']['name'] for table in new_fields ]
        res_ids = [ resources[key] for key in existing ] + [ table['resource_id'] for table in new_fields ]
        self.push_settings('tables',','.join(tables))
        self.push_settings('resources',','.join(res_ids))
        print 'done'        
       
                
    def push(self):

        if len(self.args) >= 3:
            fname = self.args[1]
            table = self.args[2]
        else:
            if len(self.args) == 2:
                fname = self.args[1]
                table = fname.split('/')[-1].split('.')[0]
            else:    
                print "USAGE: push <csvfile> <table>"
                return

        resources = base.get_resources()
        res = base.resources.get(table,False)
        
        if not res:
            if table in resources.values():
                res = table
            else:
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
        
        reader = csv.reader(infile, delimiter=',')
        reader.next()
        data = []
        for row in reader:
            data.append(dict(zip(fields,row[1:])))
            if len(data) == 50:
                self.local.action.datastore_upsert(resource_id=res,records=data,method='insert')
                print '.',
                data = []
        if len(data):
            self.local.action.datastore_upsert(resource_id=res,records=data,method='insert')
   
    def flush(self):
        table = self.args[1]
        if table in ['user','socket','gsmcell','mobilenetwork','wifinetwork','minerlog','notification','networktraffic']:
            return
        resources = base.get_resources()
        self.local.action.datastore_delete(resource_id=resources[table])
        
    def do_task(self):
        from ckan.lib.celery_app import celery
        celery.send_task("NAME."+self.args[1], task_id=str(uuid.uuid4()))
                        
    def push_cells(self):
        try:
            cell_file = open(self.args[1],'rb')
        except:
            return
        
        resources = base.get_resources()
        timestamp = datetime.now().isoformat()
        
        all_the_mcc = [ record['mcc'] for record in self.local.action.datastore_search_sql(sql=select(['mcc'],'gsmcell',ne={'mcc':'None'}))['records'] ]
        
        mnc_map = dict([ (mcc,all_the_mnc(mcc)) for mcc in all_the_mcc ])
                
        lac_map = {}        
                
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
                    lac_key = smcc+'_'+smnc
                    lac = chunks[idx['lac']]
                    if not lac_map.get(lac_key,False):
                        sql_query = select(['lac'],'gsmcell',eq={'mcc':smcc,'mnc':smnc})
                        lac_map[lac_key] = dict([ (r['lac'],True) for r in self.local.action.datastore_search_sql(sql=sql_query)['records'] ])
                    if lac_map[lac_key].get(lac,False):
                        cid = chunks[idx['cid']]
                        ex_eq = {'mcc':mcc,'mnc':mnc,'lac':lac,'cid':cid}
                        ex_query = 'cid NOT IN (' + select(['cid::text'],'gsmlocation',eq=ex_eq) + ')'
                        eq = {'mcc':smcc,'mnc':smnc,'lac':str(lac),'cid':str(cid)}
                        sql_query = select(['cid'],'gsmcell',eq=eq,where=[ex_query])
                        #sql_query = select(['cid'],'gsmcell',eq=eq)
                        #try:
                        insert = len(self.local.action.datastore_search_sql(sql=sql_query)['records']) > 0
                        #except:
                        #    sql_query = select(['cid'],'gsmcell',eq=eq)
                        #    insert = len(self.local.action.datastore_search_sql(sql=sql_query)['records']) > 0
                            
                        if insert:
                            found += 1
                            sfound = str(found)
                            rendered_cell = {'mcc':mcc, 'mnc':mnc, 'lac':lac, 'cid':cid, 'lat':chunks[idx['lat']], 'lon':chunks[idx['lon']],
                                'changeable':change(chunks[idx['changeable']]), 'retrieved':timestamp}
                            print "Found: "+','.join([ rendered_cell[f] for f in ['mcc','mnc','lac','cid'] ])
                            self.local.action.datastore_upsert(resource_id=resources['gsmlocation'],records=[rendered_cell],method='insert')
            last_mcc = mcc
            last_mnc = mnc
            
    def gsm_test(self):
        location_resource = resources.get('gsmlocation')
        cell_filter = lambda c: dict([ (key,int(c[key])) for key in ['mcc','mnc','lac','cid'] ])
        location_getter = lambda c: self.local.action.datastore_search(resource_id=location_resource,filters=cell_filter(c))['records']
        
        for uid in get_users():
            sql_query = select(['mcc','mnc','lac','cid'],'gsmcell',eq={'uid':uid},ne={'cid':'None'})
            cells = self.local.action.datastore_search_sql(sql=sql_query)['records']
            hits = len(filter(lambda c: len(c) > 0, [ location_getter(cell) for cell in cells ]))
            print "User " + str(uid) + " has " + str(len(cells)) + " cells, of which " + str(hits) + " have locations."
                    

           
            
            
        
