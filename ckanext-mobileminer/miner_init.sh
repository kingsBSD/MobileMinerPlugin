#!/bin/bash
cd /usr/lib/ckan/default
source ./bin/activate
cd src/ckanext-mobileminer
paster mobileminer init
for f in data/*.csv; do paster mobileminer push $f; done
