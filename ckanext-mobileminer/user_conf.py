import sys
import ConfigParser
import pexpect
import requests
from bs4 import BeautifulSoup

user = sys.argv[1]
pw = sys.argv[2]

server = pexpect.spawn('paster serve /etc/ckan/default/ckan.ini')
server.expect('\r\n')
server.expect('\r\n')
url = server.before.split()[-1]

def get_api_key():
    req = requests.post(url+'/login_generic?came_from=/user/logged_in',data={'login':user,'password':pw})
    soup = BeautifulSoup(req.text)
    if len(soup.find_all(attrs={'class':'error-explanation'})) <> 0:
        return False
    cookies = req.history[0].cookies
    req = requests.get(url+'/user/'+user,cookies=cookies)
    soup = BeautifulSoup(req.text)
    return soup.find_all('dd')[-1].code.text

api_key = get_api_key()
if not api_key:
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
    api_key = get_api_key()
    
config = ConfigParser.SafeConfigParser()
config.read('/etc/ckan/default/mobileminer.ini')
config.set('settings','api_key',api_key)
with open('/etc/ckan/default/mobileminer.ini', 'wb') as configfile:
    config.write(configfile)
    

 


