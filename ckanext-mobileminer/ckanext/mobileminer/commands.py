# Licensed under the Apache License Version 2.0: http://www.apache.org/licenses/LICENSE-2.0.txt

__author__ = 'Giles Richard Greenway'

from paste.script.command import Command
from ckan.logic import ValidationError 
import ckanapi
import ConfigParser
import uuid
import ast
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
        import ast
        if action == 'init':
            self.init()
        
        if action == 'minertables':
            self.minertables()

        if action == 'create_views':
            self.create_views()

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

        if action == 'drop_table':
            self.drop_table()
            
        if action == 'refresh_tables':
            self.refresh_tables()
    
    def push_settings(self,key,value):
        new_config = ConfigParser.SafeConfigParser()
        new_config.read('/etc/ckan/default/mobileminer.ini')
        new_config.set('generated',key,value)
        with open('/etc/ckan/default/mobileminer.ini', 'wb') as configfile:
            new_config.write(configfile)
       
    def init(self):
        pars = dict([ (key,self.config.get('settings',key)) for key in ['name','title','notes','owner_org'] ])
        try:
            self.local.action.organization_create(**{'name':'kcl', 'title':"King's College London"})
        except:
            assert False
        try:
            package_id = self.local.action.package_create(**pars)['id']
            self.push_settings('package_id',package_id)
        except ValidationError as invalid:
             if invalid.error_dict['name'][0] <> 'That URL is already in use.':
                return
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
        self.local.action.resource_view_create(resource_id=resources[table],title='default view',view_type='recline_view')
        print 'done'        
       
    def create_views(self):
        resources = base.get_resources()
        for table in resources.keys():
            self.local.action.resource_view_create(resource_id=resources[table],title='default view',view_type='recline_view')
        
       
    def refresh_tables(self):
        tables = dict([ (r['name'],r['id']) for r in self.local.action.package_show(id='mobileminer')['resources'] ])
        self.push_settings('tables',','.join(tables.keys()))
        self.push_settings('resources',','.join([ tables[key] for key in tables.keys() ]))
                
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
        res = resources.get(table,False)
        
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
            print "Can't open "+fname
        
        clean_text = lambda t: filter(lambda c: c == '\n' or 32 <= ord(c) <= 126,t)

        
        field_types = self.config.get(table,'field_types').split(',')
        is_list = [ ft[-2:] == '[]' for ft in field_types ]
        if True in is_list:
            row_getter = lambda r: [ [ clean_text(i) for i in ast.literal_eval(e[1]) ] if is_list[e[0]] else clean_text(e[1]) 
            for e in enumerate(r[1:]) ] 
        else:
            row_getter = lambda r: r[1:]
        
        reader = csv.reader(infile, delimiter=',')
        reader.next()
        data = []
        for row in reader:
            data.append(dict(zip(fields,row_getter(row))))
            if len(data) == 128:
                self.local.action.datastore_upsert(resource_id=res,records=data,method='insert')
                #print '.',
                data = []
        if len(data):
            self.local.action.datastore_upsert(resource_id=res,records=data,method='insert')
   
    def flush(self):
        table = self.args[1]
        if table in ['user','socket','gsmcell','mobilenetwork','wifinetwork','minerlog','notification','networktraffic']:
            return
        resources = base.get_resources()
        self.local.action.datastore_delete(resource_id=resources[table])
    
    def drop_table(self):
         tables = self.args[1]
         resources = base.get_resources()
         if tables == 'all':
            kill = resources.values()
         else:
            existing = resources.keys()
            kill = [ resources.get(tab) for tab in tables.split(',') if tab in existing ]
         for tab in kill:
            self.local.action.datastore_delete(resource_id=resources[tab]) 
            
    
    def do_task(self):
        from ckan.lib.celery_app import celery
        celery.send_task("NAME."+self.args[1], task_id=str(uuid.uuid4()))
                        
    def push_cells(self):
        try:
            cell_file = open(self.args[1],'rb')
        except:
            print "Can't open: "+self.args[1]
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
        
        idx = {'mcc':1, 'mnc':2, 'lac':3, 'cid':4, 'lon':6, 'lat':7, 'changeable':10 }
        change = lambda x: x
                        
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
                                'changeable':chunks[idx['changeable']], 'retrieved':timestamp}
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
                    

           
            
            
        
