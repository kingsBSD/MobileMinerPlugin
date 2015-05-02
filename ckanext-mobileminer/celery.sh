#!/bin/bash
cd /usr/lib/ckan/default
source ./bin/activate
cd src/ckan
export CKAN_CONFIG=/etc/ckan/default/ckan.ini
export C_FORCE_ROOT=True
paster celeryd --config=/etc/ckan/default/ckan.ini