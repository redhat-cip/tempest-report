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

import ConfigParser
import datetime
import logging
import os
import pkgutil
import Queue
import re
import subprocess
import tempest
import tempfile
import threading
import time
import urlparse


import keystoneclient.generic.client
import keystoneclient.v2_0
import glanceclient
import neutronclient.common.clientmanager
import novaclient.client
import tempest.config

from tempest_report import settings


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


def service_summary(successful_tests):
    services = {}
    for test in successful_tests:
        service = [service for prefix, service in settings.service_names.items()
                   if prefix in test]
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


def get_flavors(user, password, tenant_name, url, version=2):
    """ Returns list of available flavors """

    client_class = novaclient.client.get_client_class(version)
    nova_client = client_class(user, password, tenant_name, url)
    return nova_client.flavors.list()


def get_smallest_flavor(flavors):
    """ Takes a list of flavors and returns smallest one """

    smallest_flavor = flavors[0]
    for flavor in flavors:
        if flavor.vcpus <= smallest_flavor.vcpus:
            if flavor.disk <= smallest_flavor.disk:
                if flavor.ram < smallest_flavor.ram:
                    smallest_flavor = flavor
    return smallest_flavor


def get_keystone_client(keystone_url):
    """ Tries to discover keystone and returns v2 client """
    root = keystoneclient.generic.client.Client()
    versions = root.discover(keystone_url)
    if versions:
        keystone_url = versions.get('v2.0', {}).get('url')
        if keystone_url:
            return (keystoneclient.v2_0.client.Client, keystone_url)
    raise Exception("Keystone not found.")


def get_tenants(user, password, keystone_url, keystone_client):
    """ Authenticate user and return list of tenants """
    keystone = keystone_client(username=user,
                               password=password,
                               auth_url=keystone_url)

    return (keystone.tenants.findall(),
            keystone.auth_ref['token']['id'])


def get_services(tenant_name, token_id, keystone_url, keystone_client):
    """ Returns list of services and a scoped token """

    keystone = keystone_client(auth_url=keystone_url,
                               token=token_id,
                               tenant_name=tenant_name)

    # Create a dict of servicetype: endpoints
    services = {}
    for service in keystone.auth_ref['serviceCatalog']:
        service_type = service['type']
        endpoint = service['endpoints'][0]['publicURL']
        if service_type not in services:
            services[service_type] = endpoint
    return (services, keystone.auth_ref['token'])


def get_images(token_id, url):
    """ Returns list of available images.

    Requires a scoped token_id. """

    parsed = urlparse.urlparse(url)
    url = "%s://%s" % (parsed.scheme, parsed.netloc)
    try:
        glance = glanceclient.Client(2, url, token=token_id)
    except glanceclient.exc.HTTPNotFound:
        glance = glanceclient.Client(1, url, token=token_id)
    return [img for img in glance.images.list()]


def get_smallest_image(images):
    """ Returns the smallest active image from an image list """

    size = None
    smallest_image = None

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


def customized_tempest_conf(user, password, keystone_url, fileobj, tenant_name=None):
    keystone_client, keystone_url = get_keystone_client(keystone_url)
    tenants, token = get_tenants(user, password, keystone_url, keystone_client)

    if tenant_name is None:
        if len(tenants) > 1:
            print "Found %d tenants, using %s for current job." % (len(tenants), tenants[0].name)
            print "Please set other tenant on command line if required. "
        tenant_name = tenants[0].name

    services, _scoped_token = get_services(tenant_name, token, keystone_url, keystone_client)

    flavors = get_flavors(user, password, tenant_name, keystone_url)
    smallest_flavor = get_smallest_flavor(flavors)

    imageservice_url = services.get('image')
    images = get_images(_scoped_token.get('id'), imageservice_url)
    smallest_image = get_smallest_image(images)

    try:
        network_id = get_external_network_id(keystone_url, user, password, tenant_name)
    except Exception as ex:
        network_id = 0

    write_conf(user, password, keystone_url, tenant_name, smallest_image.id,
               smallest_flavor.id, fileobj, services, network_id)


def write_conf(user, password, keystone_url, tenant, image_id,
               flavor_id, fileobj, services, network_id):

    cfg = tempest.config.TempestConfig()

    tempest_config = ConfigParser.SafeConfigParser()
    tempest_config.set('DEFAULT', 'use_stderr', 'False')
    tempest_config.set('DEFAULT', 'log_file', 'tempest.log')

    # Create empty sections
    for section, _settings in vars(cfg).items():
        if not tempest_config.has_section(section):
            tempest_config.add_section(section)

    # Essential settings
    tempest_config.set('identity', 'uri', keystone_url)

    tempest_config.set('identity', 'username', user)
    tempest_config.set('identity', 'alt_username', user)
    tempest_config.set('identity', 'admin_username', user)

    tempest_config.set('identity', 'password', password)
    tempest_config.set('identity', 'alt_password', password)
    tempest_config.set('identity', 'admin_password', password)

    tempest_config.set('identity', 'tenant_name', tenant)
    tempest_config.set('identity', 'alt_tenant_name', tenant)
    tempest_config.set('identity', 'admin_tenant_name', tenant)
    tempest_config.set('identity', 'admin_role', tenant)

    tempest_config.set('object_storage', 'operator_role', tenant)

    tempest_config.set('compute', 'image_ref', image_id)
    tempest_config.set('compute', 'image_ref_alt', image_id)
    tempest_config.set('compute', 'allow_tenant_isolation', "False")
    tempest_config.set('compute', 'flavor_ref', flavor_id)
    tempest_config.set('compute', 'flavor_ref_alt', flavor_id)

    tempest_config.set('network', 'public_network_id', str(network_id))

    run_services = [('volume', 'cinder'),
                ('image','glance'),
                ('object-store','swift'),
                ('compute','nova'),
                ('network','neutron'),
                ]

    for service, name in run_services:
        run = "True" if services.get(service) else "False"
        tempest_config.set('service_available', name, run)

    with fileobj:
        tempest_config.write(fileobj)


def worker(queue, successful_tests, successful_subtests, verbose=False):
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

    configfile = tempfile.NamedTemporaryFile(delete=False)
    customized_tempest_conf(options.os_username, options.os_password,
                            options.os_auth_url, configfile,
                            options.os_tenant_name)

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

    failed_tests = '\n'.join([t for t in all_tests if t not in successful_tests])
    if failed_tests:
        logger.info("\nFailed tests:\n%s" % failed_tests)

    if successful_tests:
        logger.info("\nSuccessful tests:\n%s" % ('\n'.join(successful_tests)))

    summary = ""
    passed_tests = successful_tests + successful_subtests
    for _, service in service_summary(passed_tests).items():
        summary += "\n%s: %s\n" % (service.name, service.release_name)
        for feature in service.features:
            summary += "\t\t\t\t%s\n" % (feature,)
    logger.info(summary)

    os.remove(configfile.name)


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
    except Exception as ex:
        networks = []
    
    external_networks = [net for net in networks if net.get('router:external')]
    if external_networks:
        return external_networks[0].get('id')
    return None

