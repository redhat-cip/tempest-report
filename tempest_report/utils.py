# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
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

#pylint:disable=E1101

""" This file is contains three sections:

    1. Methods to detect settings, for example smallest flavor, smallest img,
       services and generating the tempest.conf file
    2. Methods to create a summary of the tests
    3. Methods to execute the tests """


import ConfigParser
import datetime
import logging
import os
import pkgutil
import Queue
import random
import re
import string
import StringIO
import subprocess
import sys
import tempest
import tempfile
import threading
import time
import urlparse

from keystoneclient.v2_0.client import Client
import keystoneclient
import glanceclient
import neutronclient.common.clientmanager
import novaclient.client
import novaclient
import tempest.config

from tempest_report import settings

# Methods to detect settings, for example smallest flavor,
# smallest img, services and generating the tempest.conf file


def get_flavors(user, password, tenant_name, url, version=2):
    """ Returns list of available flavors """

    client_class = novaclient.client.get_client_class(version)
    nova_client = client_class(user, password, tenant_name, url)
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
   

def get_images(services, token):
    """ Returns list of available images. """

    image_url = services.get('image')
    if image_url:
        parsed = urlparse.urlparse(image_url)
        url = "%s://%s" % (parsed.scheme, parsed.netloc)
        try:
            glance = glanceclient.Client(2, url, token=token.get('id'))
        except glanceclient.exc.HTTPNotFound:
            glance = glanceclient.Client(1, url, token=token.get('id'))
        return [img for img in glance.images.list()]
    return None


def get_smallest_image(images):
    """ Returns the smallest active image from an image list """

    size = sys.maxint
    smallest_image = None

    for img in images:
        if (img.size < size and
            img.disk_format in ['qcow2', 'ami'] and
            img.visibility == 'public' and
                img.status == 'active'):
            size = img.size
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


def create_tenant_and_user(username, password, auth_url, tenant_name):
    keystone = keystoneclient.v2_0.client.Client(username=username,
                                                 password=password,
                                                 auth_url=auth_url,
                                                 tenant_name=tenant_name)

    username = ''.join(random.choice(string.letters) for x in range(10))
    tenant_name = ''.join(random.choice(string.letters) for x in range(10))
    password = ''.join(random.choice(string.letters) for x in range(10))
    email = ''.join(random.choice(string.letters) for x in range(5)) + 'dummy@dummy.org'

    tenant = keystone.tenants.create(tenant_name=tenant_name,
                                     description="Tenant for tempest",
                                     enabled=True)
    user = keystone.users.create(username, password, email, tenant.id)

    return {'username': username,
            'password': password,
            'tenant_name': tenant_name,
            'tenant_id': tenant.id,
            'user_id': user.id}


def delete_tenant_and_user(username, password, auth_url, tenant_name, user):
    keystone = keystoneclient.v2_0.client.Client(username=username,
                                                 password=password,
                                                 auth_url=auth_url,
                                                 tenant_name=tenant_name)
    keystone.users.delete(user['user_id'])
    keystone.tenants.delete(user['tenant_id'])


def customized_tempest_conf(users, keystone_url):
    user = users['admin_user']['username']
    password = users['admin_user']['password']
    tenant_name = users['admin_user']['tenant_name']

    # Detect settings
    services, token = get_services(user, password, tenant_name, keystone_url)

    smallest_flavor_id = ""
    flavors = get_flavors(user, password, tenant_name, keystone_url)
    if flavors:
        smallest_flavor = get_smallest_flavor(flavors)
        smallest_flavor_id = smallest_flavor.id

    smallest_image_id = ""
    images = get_images(services, token)
    if images:
        smallest_image = get_smallest_image(images)
        smallest_image_id = smallest_image.id

    try:
        network_id = get_external_network_id(keystone_url, user,
                                             password, tenant_name)
    except Exception:
        network_id = 0

    # Create tempest config, add default sections
    cfg = tempest.config.TempestConfig()
    tempest_config = ConfigParser.SafeConfigParser()
    for section, _settings in vars(cfg).items():
        if not tempest_config.has_section(section):
            tempest_config.add_section(section)

    tempest_config.set('DEFAULT', 'use_stderr', 'False')
    tempest_config.set('DEFAULT', 'log_file', 'tempest.log')
    tempest_config.set('DEFAULT', 'lock_path', '/tmp')

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

    tempest_config.set('identity', 'tenant_name',
                       users['first_user']['tenant_name'])
    tempest_config.set('identity', 'alt_tenant_name',
                       users['second_user']['tenant_name'])
    tempest_config.set('identity', 'admin_tenant_name',
                       users['admin_user']['tenant_name'])
    tempest_config.set('identity', 'admin_role',
                       users['admin_user']['tenant_name'])

    tempest_config.set('object_storage', 'operator_role',
                       users['admin_user']['tenant_name'])

    tempest_config.set('compute', 'image_ref', smallest_image_id)
    tempest_config.set('compute', 'image_ref_alt', smallest_image_id)
    tempest_config.set('compute', 'flavor_ref', smallest_flavor_id)
    tempest_config.set('compute', 'flavor_ref_alt', smallest_flavor_id)

    if users['first_user'] != users['second_user']:
        tempest_config.set('compute', 'allow_tenant_isolation', "True")
        tempest_config.set('compute', 'allow_tenant_reuse', "True")
    else:
        tempest_config.set('compute', 'allow_tenant_isolation', "False")
        tempest_config.set('compute', 'allow_tenant_reuse', "False")

    if network_id is not None:
        tempest_config.set('network', 'public_network_id', str(network_id))

    run_services = [('volume', 'cinder'),
                    ('image', 'glance'),
                    ('object-store', 'swift'),
                    ('compute', 'nova'),
                    ('network', 'neutron'),
                    ]

    for service, name in run_services:
        run = "True" if services.get(service) else "False"
        tempest_config.set('service_available', name, run)

    fileobj = StringIO.StringIO()
    tempest_config.write(fileobj)
    return fileobj.getvalue()


""" Methods to create a summary of the tests """


class ServiceSummary(object):
    def __init__(self, name, *_args, **_kwargs):
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

    def get_features(self):
        return sorted(self.features)


def service_summary(successful_tests):
    services = {}
    for test in successful_tests:
        service = [service
                   for prefix, service in settings.service_names.items()
                   if prefix in str(test)]
        if service:
            service_name = service[0]
            if not service_name in services:
                services[service_name] = ServiceSummary(service_name)
            result = settings.description_list.get(str(test))
            if result:
                release = result.get('release', 0)
                feature = result.get('feature')
                services[service_name].set_release(release)
                services[service_name].add_feature(feature)
    return services


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


"""  Methods to execute the tests """


def executer(testname, configfile):
    """ Execute a single test """

    _environ = dict(os.environ)

    os.environ['TEMPEST_CONFIG_DIR'] = os.path.dirname(configfile)
    os.environ['TEMPEST_CONFIG'] = os.path.basename(configfile)

    success = False
    output = None

    try:
        output = subprocess.check_output(
            ["nosetests", "-v", "-s", testname],
            stderr=subprocess.STDOUT)
        success = True
        output = output
    except subprocess.CalledProcessError, error:
        output = error.output

    os.environ.clear()
    os.environ.update(_environ)

    return (success, output)


def worker(queue, successful_tests, successful_subtests, verbose=False):
    """ Single worker which will be executed as thread """

    logger = logging.getLogger('tempest_report')
    while True:
        try:
            testname, configfile_name = queue.get_nowait()
        except Queue.Empty:
            break

        success, output = executer(testname, configfile_name)

        logger.debug(output)

        if success:
            successful_tests.append(testname)
            msg = "OK:  %s" % testname
        else:
            msg = "ERR: %s" % testname

        lineend_ok = re.compile('(.*) \.\.\. ok$')
        for line in output.split('\n'):
            match = lineend_ok.match(line)
            if match and match not in successful_tests:
                successful_subtests.append(match.group(1))

        if verbose:
            logger.info(msg)
        else:
            logger.debug(msg)

        queue.task_done()


def main(options):
    now = datetime.datetime.now()
    logfile = "tempest-report-%s.log" % now.strftime("%Y%m%d-%H%M%S")
    print "Full test output logged to %s" % logfile

    logger = logging.getLogger('tempest_report')
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    logfile = logging.FileHandler(logfile)
    logfile.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    logger.addHandler(console)
    logger.addHandler(logfile)

    tenants = get_tenants(options.os_username,
                          options.os_password,
                          options.os_auth_url)

    tenant_name = options.os_tenant_name
    if tenant_name is None:
        if len(tenants) > 1:
            print "Found %d tenants, using %s for current job." % (
                len(tenants), tenants[0].name)
            print "Please set other tenant on command line if required. "
        tenant_name = tenants[0].name

    users = {'admin_user': {'username': options.os_username,
                            'password': options.os_password,
                            'tenant_name': tenant_name},
             'first_user': {'username': options.os_username,
                            'password': options.os_password,
                            'tenant_name': tenant_name},
             'second_user': {'username': options.os_username,
                             'password': options.os_password,
                             'tenant_name': tenant_name}
             }

    if options.is_admin:
        users['first_user'] = create_tenant_and_user(options.os_username,
                                                     options.os_password,
                                                     options.os_auth_url,
                                                     tenant_name)

        users['second_user'] = create_tenant_and_user(options.os_username,
                                                      options.os_password,
                                                      options.os_auth_url,
                                                      tenant_name)

    config = customized_tempest_conf(users, options.os_auth_url)

    configfile = tempfile.NamedTemporaryFile(delete=False)
    with configfile:
        configfile.write(config)

    queue = Queue.Queue()
    successful_tests = []
    successful_subtests = []
    all_tests = []

    if not options.fullrun:
        for test, values in settings.description_list.items():
            test_level = values.get('level', 1)
            release_level = values.get('release', 0)
            dummy = values.get('dummy', False)
            if (int(test_level) <= int(options.level) and
                    int(release_level) <= int(options.max_release_level) and
                    not dummy):
                queue.put((test, configfile.name))
                all_tests.append(test)
    else:
        packages = pkgutil.walk_packages(tempest.__path__, prefix="tempest.")
        for _importer, testname, _ispkg in packages:
            if "test_" in testname:
                queue.put((testname, configfile.name))
                all_tests.append(testname)

    threads = []
    for _nr in range(4):
        thread = threading.Thread(target=worker,
                                  args=(queue,
                                        successful_tests,
                                        successful_subtests,
                                        options.verbose))
        thread.daemon = True
        thread.start()
        threads.append(thread)

    while True:
        try:
            if len([t for t in threads if t.isAlive()]) == 0:
                break
            time.sleep(1)
        except KeyboardInterrupt:
            break

    os.remove(configfile.name)
    if options.is_admin:
        delete_tenant_and_user(options.os_username,
                               options.os_password,
                               options.os_auth_url,
                               tenant_name,
                               users['first_user'])
        delete_tenant_and_user(options.os_username,
                               options.os_password,
                               options.os_auth_url,
                               tenant_name,
                               users['second_user'])

    failed_tests = '\n'.join(sorted(
        [t for t in all_tests if t not in successful_tests]))
    if failed_tests:
        logger.info("\nFailed tests:\n%s" % failed_tests)

    if successful_tests:
        logger.info("\nSuccessful tests:\n%s" %
                    ('\n'.join(sorted(successful_tests))))

    summary = ""
    passed_tests = successful_tests + successful_subtests
    for _, service in sorted(service_summary(passed_tests).items()):
        summary += "\n%s: %s\n" % (service.name, service.release_name)
        for feature in service.get_features():
            summary += "\t\t\t\t%s\n" % (feature,)
    logger.info(summary)
