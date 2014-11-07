from ghost import Ghost
from bs4 import BeautifulSoup

property_getters = {'name':lambda s: s.find_all(attrs={'itemprop':'name','class':'document-title'})[0].div.text,
    'developer':lambda s: s.find_all(attrs={'itemprop':'author'})[0].span.text,
    'category':lambda s: s.find_all(attrs={'itemprop':'genre'})[0].text,
    'price':lambda s: s.find_all(attrs={'class':'price buy'})[0].find_all(attrs={'itemprop':'price'})[0]['content'],
    'description':lambda s: s.find_all(attrs={'class':'id-app-orig-desc'})[0].text,
    'content_rating': lambda s: s.find_all(attrs={'class':'content','itemprop':'contentRating'})[0].text.strip()}

def get_app_details(package):
    gh=Ghost(wait_timeout=999)
    page,page_name = gh.create_page()
    url = 'https://play.google.com/store/apps/details?id='+package
    try: 
        page_res = page.open(url,wait_onload_event=True)
    except:
        print "Can't find: "+package
        return {}
    try:
        page.click("button.id-view-permissions-details")
    except:
        return {}
    page.wait_for_selector("div.permissions-heading")
    soup = BeautifulSoup(page.content)
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

