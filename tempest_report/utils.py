# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>

import os
import pkgutil
import subprocess
from urlparse import urlparse

import requests

from tempest_report import settings
from tempest_report.settings import name_mapping


from keystoneclient.v2_0 import client
import glanceclient
import novaclient

from tempest import config
import tempfile
import ConfigParser
import sys


class ServiceSummary(object):
    def __init__(self, name, *args, **kwargs):
        self.name = name 
        self.release = 0
        self.features = []
        self.release_name = ''

    def __repr__(self, *args, **kwargs):
        return str(self.name)

    def set_release(self, release):
        if release > self.release:
            self.release = release
            self.release_name = settings.name_mapping.get(
                release, '')
    
    def add_feature(self, feature):
        if feature and feature not in self.features:
            self.features.append(feature)


def service_summary(successful_tests):
    services = {}
    for test in successful_tests:
        result = settings.description_list.get(str(test))
        if result:
            service = result.get('service')
            release = result.get('release')
            feature = result.get('feature')
            
            if not service in services:
                services[service] = ServiceSummary(service)
            
            services[service].set_release(release)
            services[service].add_feature(feature)

    return services


def executer(testname, configfile):
    """ Execute a single test """ 

    _environ = dict(os.environ)

    config_dir = os.path.dirname(configfile) 
    config_file = os.path.basename(configfile) 

    if config_dir:
        os.environ['TEMPEST_CONFIG_DIR'] = config_dir

    if config_file:
        os.environ['TEMPEST_CONFIG'] = config_file
   
    success = False
    output = None

    try:
        output = subprocess.check_output(
            ["nosetests", "-v", testname],
            stderr=subprocess.STDOUT)
        success = True
        output = output
    except subprocess.CalledProcessError, error:
        output = error.output

    os.environ.clear()
    os.environ.update(_environ)

    return (success, output)


def get_flavors(user, password, tenant_name, url, token=None):
    client_class = novaclient.client.get_client_class(2)
    nova_client = client_class(user, password, tenant_name, url)
    return nova_client.flavors.list()


def get_smallest_flavor(user, password, tenant_name, keystone_url):
    flavors = get_flavors(user, password, tenant_name, keystone_url)
    smallest_flavor = flavors[0]
    for flavor in flavors:
        if flavor.vcpus <= smallest_flavor.vcpus:
            if flavor.disk <= smallest_flavor.disk:
                if flavor.ram < smallest_flavor.ram:
                    smallest_flavor = flavor
    return smallest_flavor


def get_tenants(user, password, keystone_url):
    """ Authenticate user and return list of tenants """
    keystone = client.Client(username=user,
                             password=password,
                             auth_url=keystone_url)
    token_id = keystone.auth_ref['token']['id']
    
    headers = {'X-Auth-Token': token_id}
    tenant_url = keystone_url + "tenants"
    response = requests.get(tenant_url, headers=headers)
    data = response.json()
    
    return (data['tenants'], token_id)


def get_services(tenant_name, token_id, keystone_url):
    """ Returns list of services and a scoped token """

    services = {}
    keystone = client.Client(auth_url=keystone_url,
                             token=token_id,
                             tenant_name=tenant_name)
    
    for service in keystone.auth_ref['serviceCatalog']:
        service_type = service['type']
        endpoint = service['endpoints'][0]['publicURL']
        if service_type not in services:
            services[service_type] = endpoint
    return (services, keystone.auth_ref['token'])


def get_images(token_id, url):
    """ Returns list of available images. 
    
    Requires a scoped token_id. """
    
    try:
        version = int(url[-1])
    except ValueError:
        version = 1

    parsed = urlparse(url)
    url = "%s://%s" % (parsed.scheme, parsed.netloc)
    glance = glanceclient.Client(version, url, token=token_id)
    return [img for img in glance.images.list()]


def get_smallest_image(user, password, keystone_url):
    """ Returns the smallest active image from Glance """

    tenants, token = get_tenants(user, password, keystone_url)
    size = None
    smallest_image = None
    for tenant in tenants:
        services, scoped_token = get_services(
            tenant['name'], token, keystone_url)
        imageservice_url = services.get('image')
        if imageservice_url:
            images = get_images(scoped_token['id'], imageservice_url)
            for img in images:
                if size is None:
                    size = img.size
                    smallest_image = img  
                if (img.size < size and 
                    img.disk_format in ['qcow2', 'ami'] and
                    img.status == 'active'):
                    size = img.size
                    smallest_image = img  
    return smallest_image


def customized_tempest_conf(user, password, keystone_url, fileobj):
    tenants, token = get_tenants(user, password, keystone_url)
    tenant_id = tenants[0]['id'] 
    tenant_name = tenants[0]['name'] 
    
    url = keystone_url
    services, scoped_token = get_services(tenant_name, token, keystone_url)
    smallest_flavor = get_smallest_flavor(user, password, tenant_name, keystone_url)
    
    smallest_image = get_smallest_image(user, password, keystone_url)
    
    cfg = config.TempestConfig()
    
    tempest_config = ConfigParser.SafeConfigParser()
    tempest_config.set('DEFAULT', 'use_stderr', 'False')
    
    for section, settings in vars(cfg).items():
        for name, value in settings.items():
            if not tempest_config.has_section(section):
                tempest_config.add_section(section)
                value = str(value)
                tempest_config.set(section, name, value)
    
    tempest_config.set('identity', 'uri', services.get('identity') + '/')
    tempest_config.set('identity', 'uri_v3', "")
    
    tempest_config.set('identity', 'username', user)
    tempest_config.set('identity', 'alt_username', user)
    tempest_config.set('identity', 'admin_username', user)
    
    tempest_config.set('identity', 'password', password)
    tempest_config.set('identity', 'alt_password', password)
    tempest_config.set('identity', 'admin_password', password)
    
    tempest_config.set('identity', 'tenant_name', tenant_name)
    tempest_config.set('identity', 'alt_tenant_name', tenant_name)
    tempest_config.set('identity', 'admin_tenant_name', tenant_name)
    tempest_config.set('identity', 'admin_role', tenant_name)
    
    tempest_config.set('object_storage', 'operator_role', tenant_name)
    
    tempest_config.set('compute', 'image_ref', smallest_image.id)
    tempest_config.set('compute', 'image_ref_alt', smallest_image.id)
    tempest_config.set('compute', 'allow_tenant_isolation', "False")
    tempest_config.set('compute', 'flavor_ref', smallest_flavor.id)
    tempest_config.set('compute', 'flavor_ref_alt', smallest_flavor.id)
    
    with fileobj:
        tempest_config.write(fileobj)
