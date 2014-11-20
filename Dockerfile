FROM ubuntu

MAINTAINER Giles Richard Greenway

ENV HOME /root
ENV CKAN_HOME /usr/lib/ckan/default
ENV CKAN_CONFIG /etc/ckan/default
ENV CKAN_DATA /var/lib/ckan

# Install required packages

RUN apt-get -q -y update

RUN DEBIAN_FRONTEND=noninteractive apt-get -q -y --fix-missing install \
        postgresql-client-9.3 \
        python-minimal \
        python-dev \
        python-virtualenv \
        libevent-dev \
        libpq-dev \
        nginx-light \
        apache2 \
        libapache2-mod-wsgi \
        postfix \
        build-essential 
        
RUN DEBIAN_FRONTEND=noninteractive apt-get -q -y --fix-missing install \                
        gfortran \
        gfortran-4.8 \
        libblas-dev \
        libblas3 \
        liblapack-dev \
        liblapack3 \
        libopenblas-base 
        
RUN DEBIAN_FRONTEND=noninteractive apt-get -q -y --fix-missing install \
	git \ 
	expect \
	supervisor \
	wget \
	nano \
	lynx \
	screen

RUN DEBIAN_FRONTEND=noninteractive apt-get -q -y --fix-missing install \
        nodejs \
        npm
RUN npm install phantomjs	
	
# Install CKAN
RUN virtualenv $CKAN_HOME
RUN mkdir -p $CKAN_HOME $CKAN_CONFIG $CKAN_DATA
RUN chown www-data:www-data $CKAN_DATA

RUN $CKAN_HOME/bin/pip install -e 'git+https://github.com/ckan/ckan.git#egg=ckan'
RUN $CKAN_HOME/bin/pip install -r $CKAN_HOME/src/ckan/requirements.txt
RUN ln -s $CKAN_HOME/src/ckan/who.ini $CKAN_CONFIG/

RUN  /bin/bash -c "source $CKAN_HOME/bin/activate;cd $CKAN_HOME/src/ckan/;paster make-config ckan /etc/ckan/default/ckan.ini"
RUN sed -i "s/port.*/port = 80/g" $CKAN_CONFIG/ckan.ini
RUN sed -i "s/<VirtualHost 0.0.0.0:8080>/<VirtualHost 0.0.0.0:80>/g" $CKAN_HOME/src/ckan/contrib/docker/apache.conf
RUN sed -i "s/sqlalchemy.url.*/sqlalchemy\.url = postgresql:\/\/ckan:ckan@db\/ckan_default/g" $CKAN_CONFIG/ckan.ini
RUN sed -i "s/#solr_url.*/solr_url = http:\/\/solr:8983\/solr/g" $CKAN_CONFIG/ckan.ini
RUN sed -i "s/#ckan.storage_path.*/ckan.storage_path = \/var\/lib\/ckan/g" $CKAN_CONFIG/ckan.ini

RUN sed -i '/^ckan.plugins.*/ s/$/ datastore mobileminer/' $CKAN_CONFIG/ckan.ini
#RUN sed -i '/^ckan.plugins.*/ s/$/ datastore/' $CKAN_CONFIG/ckan.ini

RUN sed -i "s/#ckan.datastore.write_url.*/ckan.datastore.write_url = postgresql:\/\/ckan:ckan@db\/datastore_default/g" $CKAN_CONFIG/ckan.ini
RUN sed -i "s/#ckan.datastore.read_url.*/ckan.datastore.read_url = postgresql:\/\/datastore_default:datastore@db\/datastore_default/g" $CKAN_CONFIG/ckan.ini

ADD requirements.txt $CKAN_HOME/
RUN $CKAN_HOME/bin/pip install -r $CKAN_HOME/requirements.txt

RUN $CKAN_HOME/bin/pip install pexpect

RUN $CKAN_HOME/bin/pip install "ipython[notebook]"
RUN $CKAN_HOME/bin/pip install nltk
RUN $CKAN_HOME/bin/pip install matplotlib

ADD ckanext-mobileminer $CKAN_HOME/src/ckanext-mobileminer
RUN chmod a+x $CKAN_HOME/src/ckanext-mobileminer/bsdckan_init
RUN cp $CKAN_HOME/src/ckanext-mobileminer/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN cp $CKAN_HOME/src/ckanext-mobileminer/mobileminer.ini $CKAN_CONFIG
#RUN $CKAN_HOME/bin/pip install -r $CKAN_HOME/src/ckanext-mobileminer/requirements.txt
RUN  /bin/bash -c "source $CKAN_HOME/bin/activate;cd $CKAN_HOME/src/ckanext-mobileminer; python setup.py develop"

# Configure apache
RUN ln -s $CKAN_HOME/src/ckan/contrib/docker/apache.wsgi $CKAN_CONFIG/apache.wsgi
RUN ln -s $CKAN_HOME/src/ckan/contrib/docker/apache.conf /etc/apache2/sites-available/ckan_default.conf
RUN echo "Listen 80" > /etc/apache2/ports.conf
RUN echo 'export CKAN_CONFIG=/etc/ckan/default' >> /etc/apache2/envvars
RUN a2ensite ckan_default
RUN a2dissite 000-default

# Configure nginx
RUN rm /etc/nginx/nginx.conf
RUN ln -s $CKAN_HOME/src/ckan/contrib/docker/nginx.conf /etc/nginx/nginx.conf
RUN mkdir /var/cache/nginx

# Configure postfix
RUN rm /etc/postfix/main.cf
RUN ln -s $CKAN_HOME/src/ckan/contrib/docker/main.cf /etc/postfix/main.cf

RUN chmod a+x $CKAN_HOME/src/ckanext-mobileminer/bsdckan_init
RUN chmod a+x $CKAN_HOME/src/ckanext-mobileminer/notebook.sh
RUN chmod a+x $CKAN_HOME/src/ckanext-mobileminer/miner_init.sh

# Configure runit
RUN ln -s $CKAN_HOME/src/ckan/contrib/docker/svc /etc/service
#CMD ["/sbin/my_init"]
#CMD ["/bin/bash -c \"/usr/local/bin/ckan_init; service apache2 start\""]
CMD /bin/bash -c "$CKAN_HOME/src/ckanext-mobileminer/bsdckan_init"

VOLUME ["/var/lib/ckan"]
EXPOSE 80

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

