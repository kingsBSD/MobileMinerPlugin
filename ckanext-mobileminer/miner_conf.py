import os
#from subprocess import call
import sys
import ConfigParser
import pexpect
import requests
from bs4 import BeautifulSoup

user = sys.argv[1]
pw = sys.argv[2]

os.chdir('/usr/lib/ckan/default/src/ckan')
print "Starting a temporay CKAN server..."
server = pexpect.spawn('paster serve /etc/ckan/default/ckan.ini')
server.expect('\r\n')
server.expect('\r\n')
url = "http://localhost"

def get_api_key():
    req = requests.post(url+'/login_generic?came_from=/user/logged_in',data={'login':user,'password':pw})
    soup = BeautifulSoup(req.text)
    if len(soup.find_all(attrs={'class':'error-explanation'})) <> 0:
        print 'User '+user+' not found...'
        return False
    cookies = req.history[0].cookies
    req = requests.get(url+'/user/'+user,cookies=cookies)
    soup = BeautifulSoup(req.text)
    print 'Found the api key for user: '+user+'...'
    return soup.find_all('dd')[-1].code.text

api_key = get_api_key()
if not api_key:
    print 'Creating user: '+user+'...'
    paste = pexpect.spawn('paster sysadmin add '+user+' -c /etc/ckan/default/ckan.ini')
    paste.expect('User "'+user+'" not found')
    paste.expect('\r\n')
    paste.sendline('y')
    paste.expect('\r\n')
    paste.sendline('admin')
    paste.expect('\r\n')
    paste.sendline('admin')
    paste.expect('\r\n')
    paste.expect('\r\n')
    paste.readlines()
    api_key = get_api_key()
    
config = ConfigParser.SafeConfigParser()
config.read('/etc/ckan/default/mobileminer.ini')
all_the_tables = config.get('settings','tables').split(',') + config.get('settings','non_user_tables').split(',')
config.set('settings','api_key',api_key)
with open('/etc/ckan/default/mobileminer.ini', 'wb') as configfile:
    config.write(configfile)
    
#os.chdir('/usr/lib/ckan/default/src/ckanext-mobileminer')
#paste_init = pexpect.spawn('paster mobileminer init',timeout=120)
#for table in all_the_tables:
#    paste_init.expect('Creating table: '+table,timeout=120)
#    print 'Initialised table: '+table
#paste_init.expect('done')
#call(['paster','mobileminer','init'])
 

