# Licensed under the Apache License Version 2.0: http://www.apache.org/licenses/LICENSE-2.0.txt

__author__ = 'Giles Richard Greenway'

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException,NoSuchElementException

from bs4 import BeautifulSoup

property_getters = {'name':lambda s: s.find_all(attrs={'itemprop':'name','class':'document-title'})[0].div.text,
    'developer':lambda s: s.find_all(attrs={'itemprop':'author'})[0].span.text,
    'category':lambda s: s.find_all(attrs={'itemprop':'genre'})[0].text,
    'price':lambda s: s.find_all(attrs={'class':'price buy'})[0].find_all(attrs={'itemprop':'price'})[0]['content'],
    'description':lambda s: s.find_all(attrs={'class':'id-app-orig-desc'})[0].text,
    'content_rating': lambda s: s.find_all(attrs={'class':'content','itemprop':'contentRating'})[0].text.strip()}

def get_app_details(package):
    page = webdriver.PhantomJS()
    url = 'https://play.google.com/store/apps/details?id='+package
    try: 
        page.get(url)
    except:
        print "Can't find: "+package
        return {}
    try:
        button = page.find_element_by_class_name('id-view-permissions-details')
        button.click()
    except NoSuchElementException as nosuch:
         print "Can't find the permission button for " + package
    try:
        element = WebDriverWait(page, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'permissions-heading')))
    except TimeoutException as timeout:
        print "Timeout waiting for permissions: " + package
        return {}

    soup = BeautifulSoup(page.page_source)
    details = dict([ (key,property_getters[key](soup)) for key in property_getters.keys() ])
    
    perm_container = soup.find_all(attrs={'class':'permissions-container'})[0]
    perms = []
    for ul in perm_container.find_all('ul',attrs={'class':'bucket-description'}):
        for li in ul.find_all('li'):
            perms.append(li.text)
    details['permissions'] = [ perm for perm in perms if len(perm) ]
    
    details['package'] = package
    details['url'] = url
    
    return details

