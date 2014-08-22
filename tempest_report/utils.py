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


import datetime
import itertools
import logging
import os
import pkgutil
import Queue
import random
import re
import string
import subprocess
import tempfile
import threading
import time

import keystoneclient
import tempest

from tempest_report.discover import customized_tempest_conf
from tempest_report import settings


def load_excluded_tests(fname):
    """ Load the excluded tests form a flat file."""
    regexps = []
    with open(fname) as excluded_tests:
        for line in excluded_tests:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            regexps.append(re.compile(line))
    return regexps


def test_is_excluded(testname, exclude_regexps):
    """ Return True is the test is part of the exclude list."""
    def test_not_match(regex):
        return not regex.search(testname)

    failed_at = len(list(itertools.takewhile(test_not_match,
                                             exclude_regexps)))
    excluded = failed_at != len(exclude_regexps)
    return excluded


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
            if service_name not in services:
                services[service_name] = ServiceSummary(service_name)
            result = settings.description_list.get(str(test))
            if result:
                release = result.get('release', 0)
                feature = result.get('feature')
                services[service_name].set_release(release)
                services[service_name].add_feature(feature)
    return services


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

    keystone = keystoneclient.v2_0.client.Client(username=options.os_username,
                                                 password=options.os_password,
                                                 auth_url=options.os_auth_url)
    tenants = keystone.tenants.findall()

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

    excluded_tests = load_excluded_tests(options.exclude)

    if not options.fullrun:
        for test, values in settings.description_list.items():
            test_level = values.get('level', 1)
            release_level = values.get('release', 0)
            dummy = values.get('dummy', False)
            if (int(test_level) <= int(options.level) and
                    int(release_level) <= int(options.max_release_level) and
                    not dummy and
                    not test_is_excluded(test, excluded_tests)):
                queue.put((test, configfile.name))
                all_tests.append(test)
    else:
        packages = pkgutil.walk_packages(tempest.__path__, prefix="tempest.")
        for _importer, testname, _ispkg in packages:
            if ("test_" in testname and
                    not test_is_excluded(testname, excluded_tests)):
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
