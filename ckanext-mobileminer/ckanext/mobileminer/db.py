from itertools import chain
import base
resources = base.get_resources()
local = base.get_local()

quotify = lambda x: '"'+x+'"'

def quotify_field_value(table,field,value):
    if base.table_field_types[table].get(field,'bigint') == 'text':
        return "'"+str(value)+"'"
    else:
        return str(value)    
    
def value_comp(table,field,value,op='='):
    return op.join([field,quotify_field_value(table,field,value)])

def select(fields,table,eq={},gt={},lt={},ge={},ne={},where=False,group=False,having=False,order=False,page=False,page_size=128,distinct=True):
    clauses = []
    where_clause = group_clause = having_clause = order_clause = page_clause = False  
    for condition,op in [ (eq,'='), (gt,'>'), (lt,'<'), (ge,'>='), (ne,'!=') ]:
        clauses += [ value_comp(table,item[0],item[1],op) for item in condition.items() ]
    if where:
        clauses += where
    if clauses:
        where_clause = 'WHERE ' + ' AND '.join(clauses)
    if distinct:
        selecter = 'SELECT DISTINCT'
    else:
        selecter = 'SELECT'
    if group:
        group_clause = 'GROUP BY ' + group
    if having:
        having_clause = 'HAVING ' + having
    if page:
        page_clause = 'LIMIT ' + str(page_size) + ' OFFSET ' + str(page*page_size)
    if order:
        order_clause = 'ORDER BY ' + order
    return ' '.join([ s for s in [selecter,','.join(fields),'FROM',quotify(resources.get(table)),where_clause,group_clause,having_clause, page_clause, order_clause] if s ])

def all_the_mcc():
    return [ record['mcc'] for record in local.action.datastore_search_sql(sql=select(['mcc'],'gsmcell',ne={'mcc':'None'}))['records'] ]

def all_the_mnc(mcc):
    return [ record['mnc'] for record in local.action.datastore_search_sql(sql=select(['mnc'],'gsmcell',eq={'mcc':mcc}))['records'] ]

def get_users():
    return [ r['uid'] for r in local.action.datastore_search(resource_id=resources.get('user'))['records'] ]
 