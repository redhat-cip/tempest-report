# Copyright (C) 2014 eNovance SAS <licensing@enovance.com>
#
# Author: Christian Schwede <christian.schwede@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ConfigParser
import os
import optparse
import StringIO
import sys
import tempfile

from keystoneclient.v2_0.client import Client
import keystoneclient
import neutronclient.common.clientmanager
import novaclient.client
import novaclient
import tempest


def get_flavors(user, password, tenant_name, url, version=2, region_name=None):
    """ Returns list of available flavors """

    client_class = novaclient.client.get_client_class(version)
    nova_client = client_class(user, password, tenant_name, url, region_name=region_name)
    try:
        return nova_client.flavors.list()
    except novaclient.exceptions.EndpointNotFound:
        return None


def get_smallest_flavor(flavors):
    """ Takes a list of flavors and returns smallest one """

    smallest_flavor = flavors[0]
    for flavor in flavors:
        if flavor.vcpus <= smallest_flavor.vcpus:
            if flavor.disk <= smallest_flavor.disk:
                if flavor.ram < smallest_flavor.ram:
                    smallest_flavor = flavor
    return smallest_flavor


def get_tenants(user, password, keystone_url):
    """ Authenticate user and return list of tenants """
    keystone = keystoneclient.v2_0.client.Client(username=user,
                                                 password=password,
                                                 auth_url=keystone_url)

    return keystone.tenants.findall()


def get_images_from_nova(user, password, tenant_name, url, version=2, region_name=None):
    client_class = novaclient.client.get_client_class(version)
    nova_client = client_class(user, password, tenant_name, url, region_name=region_name)
    try:
        return nova_client.images.list()
    except novaclient.exceptions.EndpointNotFound:
        return None


def get_smallest_image(images):
    """ Returns the smallest active image from an image list """

    min_size = sys.maxint
    smallest_image = None

    for img in images:
        size = img._info.get('OS-EXT-IMG-SIZE:size', sys.maxint)
        if img.status == 'ACTIVE' and size < min_size:
            min_size = size
            smallest_image = img
    return smallest_image


def get_external_network_id(auth_url, username, password, tenant_name):
    client_manager = neutronclient.common.clientmanager.ClientManager(
        auth_url=auth_url,
        username=username,
        password=password,
        tenant_name=tenant_name,
        auth_strategy="keystone",
        endpoint_type='publicURL',
        api_version={'network': '2.0'}
    )

    try:
        networks = client_manager.neutron.list_networks().get('networks', {})
    except Exception:
        networks = []

    external_networks = [net for net in networks if net.get('router:external')]
    if external_networks:
        return external_networks[0].get('id')
    return None


def get_services(user, password, tenant_name, keystone_url):
    """ Returns list of services and a scoped token """
    keystone = keystoneclient.v2_0.client.Client(auth_url=keystone_url,
                                                 username=user,
                                                 password=password,
                                                 tenant_name=tenant_name)

    # Create a dict of servicetype: endpoints
    services = {}
    for service in keystone.auth_ref['serviceCatalog']:
        service_type = service['type']
        endpoint = service['endpoints'][0]['publicURL']
        if service_type not in services:
            services[service_type] = endpoint
    return (services, keystone.auth_ref['token'])


def customized_tempest_conf(users, keystone_url, image_id=None, region_name=None, flavor_id=None):
    user = users['admin_user']['username']
    password = users['admin_user']['password']
    tenant_name = users['admin_user']['tenant_name']

    # Detect settings
    services, token = get_services(user, password, tenant_name, keystone_url)

    if not flavor_id:
        smallest_flavor_id = ""
        flavors = get_flavors(user, password, tenant_name, keystone_url, region_name=region_name)
        if flavors:
            smallest_flavor = get_smallest_flavor(flavors)
            smallest_flavor_id = smallest_flavor.id
    else:
        smallest_flavor_id = flavor_id

    if not image_id:
        smallest_image_id = ""
        try:
            images = get_images_from_nova(user, password, tenant_name, keystone_url, region_name=region_name)
        except Exception:
            images = None
            del services['compute']
            del services['image']
        if images:
            smallest_image = get_smallest_image(images)
            if smallest_image:
                smallest_image_id = smallest_image.id
    else:
        smallest_image_id = image_id

    try:
        network_id = get_external_network_id(keystone_url, user,
                                             password, tenant_name)
    except Exception:
        network_id = 0

    # Create tempest config, add default sections
    tempest_config = ConfigParser.SafeConfigParser()

    tempest_config.set('DEFAULT', 'debug', 'False')
    tempest_config.set('DEFAULT', 'use_stderr', 'False')
    tempest_config.set('DEFAULT', 'log_file', 'tempest.log')
    tempest_config.set('DEFAULT', 'lock_path', '/tmp')

    tempest_config.add_section('identity')
    tempest_config.set('identity', 'uri', keystone_url)

    tempest_config.set('identity', 'username',
                       users['first_user']['username'])
    tempest_config.set('identity', 'alt_username',
                       users['second_user']['username'])
    tempest_config.set('identity', 'admin_username',
                       users['admin_user']['username'])

    tempest_config.set('identity', 'password',
                       users['first_user']['password'])
    tempest_config.set('identity', 'alt_password',
                       users['second_user']['password'])
    tempest_config.set('identity', 'admin_password',
                       users['admin_user']['password'])

    tempest_config.set('identity', 'tenant_name', '"%s"' %
                       users['first_user']['tenant_name'])
    tempest_config.set('identity', 'alt_tenant_name', '"%s"' %
                       users['second_user']['tenant_name'])
    tempest_config.set('identity', 'admin_tenant_name', '"%s"' %
                       users['admin_user']['tenant_name'])
    tempest_config.set('identity', 'admin_role', '"%s"' %
                       users['admin_user']['tenant_name'])

    tempest_config.add_section('identity-feature-enabled')
    tempest_config.set('identity-feature-enabled', 'api_v3', 'False')
    tempest_config.set('identity', 'uri_v3', '')

    if region_name:
        tempest_config.set('identity', 'region', region_name)
        tempest_config.set('compute', 'region', region_name)

    tempest_config.add_section('object_storage')
    tempest_config.set('object_storage', 'operator_role',
                       users['admin_user']['tenant_name'])

    tempest_config.add_section('compute')
    tempest_config.set('compute', 'image_ref', str(smallest_image_id))
    tempest_config.set('compute', 'image_ref_alt', str(smallest_image_id))
    tempest_config.set('compute', 'flavor_ref', str(smallest_flavor_id))
    tempest_config.set('compute', 'flavor_ref_alt', str(smallest_flavor_id))

    if users['first_user'] != users['second_user']:
        tempest_config.set('compute', 'allow_tenant_isolation', "True")
        tempest_config.set('compute', 'allow_tenant_reuse', "True")
    else:
        tempest_config.set('compute', 'allow_tenant_isolation', "False")
        tempest_config.set('compute', 'allow_tenant_reuse', "False")

    if network_id is not None:
        tempest_config.add_section('network')
        tempest_config.set('network', 'public_network_id', str(network_id))

    run_services = [('volume', 'cinder'),
                    ('image', 'glance'),
                    ('object-store', 'swift'),
                    ('compute', 'nova'),
                    ('network', 'neutron'),
                    ]

    tempest_config.add_section('service_available')
    for service, name in run_services:
        run = "True" if services.get(service) else "False"
        tempest_config.set('service_available', name, run)

    fileobj = StringIO.StringIO()
    tempest_config.write(fileobj)
    return fileobj.getvalue()


def main():
    parser = optparse.OptionParser(usage='''
usage: %%prog 
             [--os-username <auth-user-name>]
             [--os-password <auth-password>]
             [--os-auth-url <auth-url>]
             [--os-tenant-name <auth-tenant-name>]

Command-line interface for OpenStack Tempest.

Examples:
  %%prog --os-auth-url http://127.0.0.1:5000 \\
      --os-username user --os-password password 
'''.strip('\n') % globals())
    parser.add_option('--os-username',
                      default=os.environ.get('OS_USERNAME'),
                      metavar='<auth-user-name>',
                      help='Openstack username. Defaults to env[OS_USERNAME].')
    parser.add_option('--os-password',
                      default=os.environ.get('OS_PASSWORD'),
                      metavar='<auth-password>',
                      help='Openstack password. Defaults to env[OS_PASSWORD].')
    parser.add_option('--os-auth-url',
                      default=os.environ.get('OS_AUTH_URL'),
                      metavar='<auth-url>',
                      help='Openstack auth URL. Defaults to env[OS_AUTH_URL].')
    parser.add_option('--os-tenant-name',
                      metavar='<auth-tenant-name>',
                      default=os.environ.get('OS_TENANT_NAME'),
                      help='Openstack tenant name. '
                           'Defaults to env[OS_TENANT_NAME].')
    parser.add_option('--os-region-name',
                      metavar='<auth-region-name>',
                      default=os.environ.get('OS_REGION_NAME'),
                      help='Openstack tenant name. '
                           'Defaults to env[OS_REGION_NAME].')

    (options, args) = parser.parse_args()

    if not (options.os_username and options.os_password and options.os_auth_url):
        parser.print_usage()
        sys.exit(1)

    tenant_name = options.os_tenant_name
    if tenant_name is None:
        tenants = get_tenants(options.os_username,
                              options.os_password,
                              options.os_auth_url)

        if len(tenants) > 1:
            print "Found %d tenants, using %s for current job." % (
                len(tenants), tenants[0].name)
            print "Please set other tenant on command line if required. "
        tenant_name = tenants[0].name

    users = {}
    for user in ['admin_user', 'first_user', 'second_user']:
        users[user] = {'username': options.os_username,
                       'password': options.os_password,
                        'tenant_name': tenant_name}

    config = customized_tempest_conf(users, options.os_auth_url)

    configfile = tempfile.NamedTemporaryFile(prefix='tempest_conf_', delete=False)
    with configfile:
        configfile.write(config)

    print "Configuration written to %s" % configfile.name
    print "Set TEMPEST_CONFIG_DIR and TEMPEST_CONFIG to use this file:"
    print "export TEMPEST_CONFIG_DIR=%s" % os.path.dirname(configfile.name)
    print "export TEMPEST_CONFIG=%s" % configfile.name


if __name__ == "__main__":
    main()
