import base
from db import select
from ckan.lib.celery_app import celery
from celery.task.sets import subtask
from celery import group
from itertools import chain
import dateutil.parser
from datetime import datetime
import requests
import json

from st_cluster import cluster

def task_imports():
  return ['ckanext.mobileminer.tasks']

resources = base.get_resources()
local = base.get_local()

open_cell_key = base.config.get('settings', 'open_cell_key')
open_cell_url = base.config.get('settings', 'open_cell_url')

def get_users():
    return [ r['uid'] for r in local.action.datastore_search(resource_id=resources.get('user'))['records'] ]

def get_user_apps(uid):
    return [ r['process'] for r in local.action.datastore_search(resource_id=resources.get('userapps'), filters={'uid':uid}, sort='process')['records'] ]
    
def get_cell(mcc,mnc,lac,cellid):
    print ','.join([mcc,mnc,lac,cellid])
    payload = {'key':open_cell_key,'mcc':mcc,'mnc':mnc,'lac':lac,'cellid':cellid,'format':'json'}
    res = requests.get(open_cell_url, params=payload)
    try:
        print res.text
        raw = json.loads(res.text)
        return {'mcc':mcc, 'mnc':mnc, 'lac':lac, 'cid':raw['cellid'],
            'lat':raw['lat'], 'lon':raw['lon'], 'changeable':raw['changeable'], 'reterieved':datetime.now().isoformat()}
    except:
        return False
    
# http://stackoverflow.com/questions/13271056/how-to-chain-a-celery-task-that-returns-a-list-into-a-group
@celery.task(name = "NAME.dmap")
def dmap(it, callback):
    # Map a callback over an iterator and return as a group
    callback = subtask(callback)
    return group(callback.clone([arg,]) for arg in it)()

def for_all_users(job):
    (user_list.s() | dmap.s(job.s())).delay()

@celery.task(name = "NAME.userappsupdate")
def build_user_apps():
    for uid in get_users():
        #print uid
        for table,field in [('socket','process'),('networktraffic','process'),('notification','package')]:
            ex_query = field+' NOT IN (' + select(['process'],'userapps',eq={'uid':uid}) + ')'
            sql_query = select([field],table,eq={'uid':uid},where=[ex_query])
            #print sql_query
            records = [ {'uid':uid,'process':r[field]} for r in local.action.datastore_search_sql(sql=sql_query)['records'] ]
            local.action.datastore_upsert(resource_id=resources['userapps'],records=records,method='insert')

@celery.task(name = "NAME.dailyappusageupdate")
def daily_usage_update():
    
    mget = lambda t,d,v: d.get(t,{}).get(v,0)
    
    def builder(table,time_field,proc_field='process',conditions={},total=False):
        try:
            max_date = local.action.datastore_search_sql(sql=select(['MAX(date)'],'dailyappusage',eq={'uid':uid,'process':app}))['records'][0]['max']
        except:
            max_date = None
        if max_date:
            gt = {time_field,max_date}
        else:
            gt = {}
        date_cond = "date_trunc('day',"+time_field+")"
        selecter = ["COUNT(*)",date_cond]
        if total:
            selecter.append('SUM('+total+')')
            fields = ['count','sum']
        else:
            fields = ['count']
        cond = dict(conditions.items() + [('uid',uid),(proc_field,app)])
        sql_query = select(selecter,table,eq=cond, gt=gt,
            having='COUNT(*) > 0',group=date_cond,distinct=False)
        return dict([ (rec['date_trunc'],dict([ (field,rec[field]) for field in fields ])) for rec in local.action.datastore_search_sql(sql=sql_query)['records']
            if rec.get('date_trunc',False) ])
    
    for uid in get_users():
        print uid
        for app in get_user_apps(uid):
                        
            print app
            sockets = builder('socket','opened')
            notifications = builder('notification','time',proc_field='package') 
            rx_traffic = builder('networktraffic','start',conditions={'tx':0},total='bytes')
            tx_traffic = builder('networktraffic','start',conditions={'tx':1},total='bytes')
            
            all_the_dates = set(chain.from_iterable([ i.keys() for i in [sockets,notifications,rx_traffic,tx_traffic] ]))
              
            data = [ {'uid':uid, 'process':app, 'sockets':mget(date,sockets,'count'), 'notifications':mget(date,notifications,'count'),
                'traffic_in':mget(date,rx_traffic,'count'), 'traffic_out':mget(date,tx_traffic,'count'),
                'data_in':int(mget(date,rx_traffic,'sum'))/1024, 'data_out':int(mget(date,tx_traffic,'sum'))/1024,
                'date':date.split('T')[0], 'day':base.weekdays[dateutil.parser.parse(date).isoweekday()] } for date in all_the_dates ]

            local.action.datastore_upsert(resource_id=resources['dailyappusage'],records=data,method='insert')

@celery.task(name = "NAME.gsmupdate")
def gsm_update():

    cell_fields = ['mcc','mnc','lac','cid']
    intervals = lambda x,y: zip(range(0,x,y),range(0,x+y,y)[1:])

    all_the_mcc = [ record['mcc'] for record in local.action.datastore_search_sql(sql=select(['mcc'],'gsmcell',ne={'mcc':'None'}))['records'] ] 
    
    for mcc in all_the_mcc:
        
        all_the_mnc = [ record['mnc'] for record in local.action.datastore_search_sql(sql=select(['mnc'],'gsmcell',eq={'mcc':mcc}))['records'] ]
        
        for mnc in all_the_mnc:
            #print mcc,mnc
            lac_search = True
            lac_page = 0
            while lac_search:
                all_the_lacs = [ record['lac'] for record in local.action.datastore_search_sql(sql=select(['lac'],'gsmcell',eq={'mcc':mcc,'mnc':mnc},page=lac_page))['records'] ]
                if len(all_the_lacs) == 0:
                    lac_search = False
                lac_page += 1
                for lac in all_the_lacs:
                    eq = {'mcc':mcc,'mnc':mnc,'lac':lac}
                    searching = True
                    page = 0
                    while searching:
                        ex_query = 'cid NOT IN (' + select(['cid::text'],'gsmlocation',eq=eq) + ')'
                        sql_query = select(['cid'],'gsmcell',eq=eq,where=[ex_query],page=page)

                        cells = [ r['cid'] for r in local.action.datastore_search_sql(sql=sql_query)['records'] ]
                        if len(cells) == 0:
                            searching = False
                        else:
                            page += 1
                            rendered_cells = [c for c in [ get_cell(mcc,mnc,lac,i) for i in cells ] if c ]
                            local.action.datastore_upsert(resource_id=resources['gsmlocation'],records=rendered_cells,method='insert')    
    return False

@celery.task(name = "NAME.usercells")
def user_cells():
    searching = True
    page = 0
    while searching:
        sql_query = select(['mcc','mnc','lac','cid','lat','lon','_id'],'gsmlocation',page=page)
        cells = local.action.datastore_search_sql(sql=sql_query)['records']
        if len(cells) == 0:
            searching = False
        page += 1
        for cell in cells:
            mcc,mnc,lac,cid = [ str(cell[key]) for key in ['mcc','mnc','lac','cid'] ]
            ref,lat,lon = [ cell[key] for key in ['_id','lat','lon'] ]
            user_search = True
            user_page = 0
            print ','.join([mcc,mnc,lac,cid])
            while user_search:
                sql_query = select(['COUNT(*)','uid'],'gsmcell',eq={'mcc':mcc,'mnc':mnc,'lac':lac,'cid':cid},group='uid',page=user_page)
                users = local.action.datastore_search_sql(sql=sql_query)['records']
                if len(users) == 0:
                    user_search = False
                user_page += 1
                for uid in [ u['uid'] for u in users ]:
                    print uid
                    local.action.datastore_delete(resource_id = resources['userlocations'],filters={'uid':uid,'cid':ref})
                local.action.datastore_upsert(resource_id = resources['userlocations'],
                    records = [ {'uid':user['uid'], 'count':user['count'], 'cid':ref, 'lat':lat, 'lon':lon} for user in users ],
                    method = 'insert')
                
@celery.task(name = "NAME.cellclusters")
def cell_clusters():
    
    def cell_getter(user):
        eq = {'uid':user}
        page = 0
        searching = True
        while searching:
            query = 'SELECT t2.lat, t2.lon, t1.time FROM "' + resources['gsmcell'] + '" AS t1 JOIN "' + resources['gsmlocation'] + '" AS t2 '
            query += 'ON t1.mcc = t2.mcc::text AND t1.mnc = t2.mnc::text AND t1.lac = t2.lac::text AND t1.cid = t2.cid::text WHERE t1.uid = ' + user
            query += ' ORDER BY t1.time LIMIT 256 OFFSET '+ str(page*256)
            cells = local.action.datastore_search_sql(sql=query)['records']
            print str(user)+' '+str(len(cells))
            #print str(len(cells))+' '+str(user)
            if len(cells) == 0:
                searching = False
            else:
                page += 1
            last_time =''
            for cell in cells:
                if cell['time'] <> last_time:
                    yield (float(cell['lat']),float(cell['lon']),dateutil.parser.parse(cell['time']))
                last_time = cell['time']        
             
    for uid in get_users():
        cluster_resource = resources['gsmclusters']
        clusters = cluster(cell_getter(uid))
        print "Found " + str(len(clusters)) + " clusters for user " + str(uid)
        if len(clusters) > 0:
            map(lambda c: c.update({'uid':uid}),clusters)
            local.action.datastore_delete(resource_id=cluster_resource,filters={'uid':uid})
            local.action.datastore_upsert(resource_id=cluster_resource,records=clusters,method='insert')
            
            

        

                
                
            
            


    