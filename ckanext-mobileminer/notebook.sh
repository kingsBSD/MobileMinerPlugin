#!/bin/bash
cd $CKAN_HOME/
source ./bin/activate
cd src
ipython notebook --ip=0.0.0.0 --port=8888 --pylab=inline --no-browser