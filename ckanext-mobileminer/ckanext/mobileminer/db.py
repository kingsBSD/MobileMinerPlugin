# Licensed under the Apache License Version 2.0: http://www.apache.org/licenses/LICENSE-2.0.txt

__author__ = 'Giles Richard Greenway'

from itertools import chain
import base
import dateutil.parser

get_weekday = lambda date: base.weekdays[dateutil.parser.parse(date).isoweekday()]

resources = base.get_resources()
local = base.get_local()

quotify = lambda x: '"'+x+'"'

get_weekday = lambda date: base.weekdays[dateutil.parser.parse(date).isoweekday()]

table_field_types = base.get_field_types()

def quotify_field_value(table,field,value):
    if table_field_types[table].get(field,'bigint') == 'text':
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
    return ' '.join([ s for s in [selecter,','.join(fields),'FROM',quotify(resources.get(table)),where_clause,group_clause,having_clause, order_clause, page_clause] if s ])


def find(fields,table,eq={},gt={},lt={},ge={},ne={},where=False,group=False,having=False,order=False,page=False,page_size=128,distinct=True):
    """Helper function to query the Postgres database of the CKAN datastore.
    
    Returns records as a list of dictionaries whose keys are the SELECTED fields.
    
    Positional arguments:
    fields -- list of fields to be returned by the SELECT statement.
    table -- name of the table to query.

    Keyword arguments:
    eq -- dictionary whose keys and values define equality condtions on fields in a WHERE clause.
    lt -- dictionary whose keys and values define "less-than" condtions on fields in a WHERE clause.
    gt -- dictionary whose keys and values define "greater-than" condtions on fields in a WHERE clause.
    ne -- dictionary whose keys and values define non-equality condtions on fields in a WHERE clause.
    where -- custom condtion appended to the WHERE clause.
    group -- contents of a GROUP BY clause.
    having -- contents of a HAVING clause.
    order -- ORDER BY clause, e.g: "date DESC"
    page -- the page of the results to return.
    page_size -- number of result per page defaults to 128.
    distinct -- return only distinct results, defaults to True
    """
    sql = select(fields,table,eq=eq,gt=gt,lt=lt,ge=ge,ne=ne,where=where,group=group,having=having,order=order,page=page,page_size=page_size,distinct=distinct)
    return local.action.datastore_search_sql(sql=sql)['records']

def search(table,filters,offset=0,limit=100):
    """Helper function for simple queries of the CKAN datastore via Solr.
    
    Returns records as a list of dictionaries whose keys are the queried table's fields.
    
    Positional arguments:
    tables -- name of the table to query.
    filters -- dictionary whose values determine those of the fields in the returned rows.
    
    Keyword arguments:
    offset -- index of the first record to return
    limit -- maximum number of records to return, defaults to 100.
    
    """
    return local.action.datastore_search(resource_id=resources.get(table), filters=filters, offset=offset, limit=limit)['records']

def all_the_mcc():
    return [ record['mcc'] for record in local.action.datastore_search_sql(sql=select(['mcc'],'gsmcell',ne={'mcc':'None'}))['records'] ]

def all_the_mnc(mcc):
    return [ record['mnc'] for record in local.action.datastore_search_sql(sql=select(['mnc'],'gsmcell',eq={'mcc':mcc}))['records'] ]

def get_users():
    return [ r['uid'] for r in local.action.datastore_search(resource_id=resources.get('user'))['records'] ]
 