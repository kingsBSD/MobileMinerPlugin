from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
    name='ckanext-mobileminer',
    version=version,
    description="Facilitates the MobileMiner app talking to Ckan.",
    long_description='''
    ''',
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Giles Greenway',
    author_email='giles.greenway@kcl.ac.uk',
    url='',
    license='Apache Version 2.0',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.mobileminer'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points='''
        [ckan.plugins]
        mobileminer=ckanext.mobileminer.plugin:MobileMinerPlugin
    ''',
)
