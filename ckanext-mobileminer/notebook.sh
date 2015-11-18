#!/bin/bash
cd $CKAN_HOME/
source ./bin/activate
cd src
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser