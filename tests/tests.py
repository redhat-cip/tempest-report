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

#pylint: disable=E1101, E1103

from Queue import Empty as QueueEmpty
import subprocess
import unittest

import mock

from tempest_report import utils, settings, discover
import tempest_report


class DummyFileObject(object):
    def __init__(self, *_args, **_kwargs):
        self.name = '/dir/dummy'
        self.content = ""

    def __exit__(self, *_args, **_kwargs):
        pass

    def __enter__(self, *_args, **_kwargs):
        pass

    def write(self, content, *_args, **_kwargs):
        self.content += content


class DummyImage(object):
    def __init__(self, size, disk_format, status, id=23,
                 visibility='public'):
        self.disk_format = disk_format
        self.status = status
        self.id = id
        self.visibility = visibility
        self._info = {'OS-EXT-IMG-SIZE:size': size}


class DummyFlavor(object):
    def __init__(self, vcpus, disk, ram, id="42"):
        self.vcpus = vcpus
        self.disk = disk
        self.ram = ram
        self.id = id


class Tenant(object):
    def __init__(self, name="Tenant Name"):
        self.name = name
        self.id = "tenant_id"


class User(object):
    def __init__(self):
        self.id = "user_id"


class KeystoneDummy(object):
    class Tenants(object):
        def findall(self):
            tenant = Tenant()
            return [tenant]

        def create(self, *_args, **_kwargs):
            return Tenant()

    class Users(object):
        def create(self, *_args, **_kwargs):
            return Tenant()

    def __init__(self, *_args, **_kwargs):
        self.auth_ref = {'token': {'id': 'token'},
                         'serviceCatalog': [{
                             'type': 'servicetype',
                             'endpoints': [{
                                 'publicURL': 'url'}]}]}
        self.tenants = self.Tenants()
        self.users = self.Users()

    def discover(self, _url):
        return {'v2.0': {'url': 'http://127.0.0.1:5000/v2'}}


class UtilTest(unittest.TestCase):

    fake_creds = ("user", "password", "tenant_name", "http://127.0.0.1:5000")

    @mock.patch('novaclient.client')
    def test_get_smallest_flavor(self, novaclient):
        sample_flavors = []
        sample_flavors.append(DummyFlavor(1, 1, 128, 42))
        sample_flavors.append(DummyFlavor(1, 0, 64, 43))
        sample_flavors.append(DummyFlavor(1, 1, 64, 44))

        novaclient_cls = novaclient.get_client_class.return_value
        novaclient_obj = novaclient_cls.return_value
        novaclient_obj.flavors.list.return_value = sample_flavors

        smallest_flavor = discover.get_smallest_flavor(*self.fake_creds)
        self.assertEqual(smallest_flavor, 43)

    @mock.patch('keystoneclient.v2_0.client.Client')
    def test_get_services(self, keystoneclient):
        keystoneclient.return_value = KeystoneDummy()
        services = discover.get_services(*self.fake_creds)

        self.assertEqual(services, {'servicetype': 'url'})

    @mock.patch('subprocess.check_output')
    def test_executer(self, subprocess_mock):
        subprocess_mock.return_value = "output"
        success, output = utils.executer(
            "testname", "/dir/filename")

        self.assertTrue(success)
        self.assertEqual(output, "output")

        subprocess_mock.assert_called_with(
            ["nosetests", "-v", "-s", "testname"],
            stderr=subprocess.STDOUT)

        subprocess_mock.side_effect = subprocess.CalledProcessError(
            1, "command", "error")
        success, output = utils.executer(
            "testname", "filename")

        self.assertFalse(success)
        self.assertEqual(output, "error")

    def test_summary(self):
        dscr = {
            'tempest.api.compute': {'service': 'Compute (Nova)',
                                    'feature': '1',
                                    'release': 5},
        }

        with mock.patch.dict(settings.description_list, dscr):
            successful_tests = ['tempest.api.compute']
            summary = utils.service_summary(successful_tests)
            assert 'Compute (Nova)' in summary
            assert '1' in summary.get('Compute (Nova)').features
            release_name = summary.get('Compute (Nova)').release_name
            self.assertEqual(release_name, 'Essex (or later)')

    def test_summary_class(self):
        summary = utils.ServiceSummary('servicename')
        self.assertEqual(summary.release_name, '')

        summary.set_release(5)
        self.assertEqual(summary.release_name, 'Essex (or later)')

        summary.set_release(999)
        self.assertEqual(summary.release_name, '')

        summary.add_feature('feature')
        summary.add_feature('feature')

        self.assertEqual(str(summary), 'servicename')
        self.assertEqual(summary.features, ['feature', ])

    @mock.patch('novaclient.client')
    def test_get_smallest_image(self, novaclient):
        images = []
        images.append(DummyImage(10, 'qcow2', 'ACTIVE'))
        images.append(DummyImage(2, 'qcow2', 'ACTIVE'))
        images.append(DummyImage(1, 'qcow2', 'other'))
        images.append(DummyImage(1, 'other', 'ACTIVE'))
        images.append(DummyImage(0, 'qcow2', 'ACTIVE', id=42,
                                 visibility='private'))

        novaclient_cls = novaclient.get_client_class.return_value
        novaclient_obj = novaclient_cls.return_value
        novaclient_obj.images.list.return_value = images

        smallest_image = discover.get_smallest_image(*self.fake_creds)
        self.assertEqual(smallest_image, 42)

    @mock.patch('keystoneclient.v2_0.client.Client')
    def test_create_tenant_and_user(self, keystone):
        utils.create_tenant_and_user("keystone_username",
                                     "keystone_password",
                                     "http://keystone_url",
                                     "tenant_name")

        keystone.assert_called_with(
            username='keystone_username',
            tenant_name='tenant_name',
            password='keystone_password',
            auth_url='http://keystone_url')

        self.assertTrue(keystone().tenants.create.called)
        self.assertTrue(keystone().users.create.called)

    @mock.patch('tempest_report.discover.get_smallest_flavor')
    @mock.patch('tempest_report.discover.get_smallest_image')
    @mock.patch('tempest_report.discover.get_external_network_id')
    @mock.patch('tempest_report.discover.get_services')
    def test_customized_tempest_conf(self,
                                     get_services,
                                     get_external_network_id,
                                     get_smallest_image,
                                     get_smallest_flavor):

        get_services.return_value = {'image': 'url'}
        get_external_network_id.return_value = 32
        get_smallest_image.return_value = 23
        get_smallest_flavor.return_value = 42

        users = {'admin_user': {'username': 'admin',
                                'password': 'admin_password',
                                'tenant_name': 'admin_tenant'},
                 'first_user': {'username': 'user',
                                'password': 'password',
                                'tenant_name': 'tenant'},
                 'second_user': {'username': 'user',
                                 'password': 'password',
                                 'tenant_name': 'tenant'}}

        content = utils.customized_tempest_conf(users, "http://keystone_url")

        self.assertIn("[DEFAULT]", content)
        self.assertIn("use_stderr = False", content)
        self.assertIn("log_file = tempest.log", content)
        self.assertIn("[compute]", content)
        self.assertIn("image_ref = 23", content)
        self.assertIn("image_ref_alt = 23", content)
        self.assertIn("allow_tenant_isolation = False", content)
        self.assertIn("flavor_ref = 42", content)
        self.assertIn("flavor_ref_alt = 42", content)
        self.assertIn("[network]", content)
        self.assertIn("public_network_id = 32", content)
        self.assertIn("[object_storage]", content)
        self.assertIn("operator_role = admin_tenant", content)
        self.assertIn("[service_available]", content)
        self.assertIn("cinder = False", content)
        self.assertIn("glance = True", content)
        self.assertIn("swift = False", content)
        self.assertIn("nova = False", content)
        self.assertIn("neutron = False", content)
        self.assertIn("[identity]", content)
        #self.assertIn("uri = keystone_url", content)
        self.assertIn("username = user", content)
        self.assertIn("alt_username = user", content)
        self.assertIn("admin_username = admin", content)
        self.assertIn("password = password", content)
        self.assertIn("alt_password = password", content)
        self.assertIn("admin_password = admin_password", content)
        self.assertIn("tenant_name = \"tenant\"", content)
        self.assertIn("alt_tenant_name = \"tenant\"", content)
        self.assertIn("admin_tenant_name = \"admin_tenant\"", content)
        self.assertIn("admin_role = \"admin_tenant\"", content)

    @mock.patch('logging.getLogger')
    @mock.patch('Queue.Queue')
    @mock.patch('tempest_report.utils.executer')
    def test_worker(self, executer, queue, logger):

        # Run once in test, than return Exception
        self.executed = False

        def side_effect(*args, **kwargs):
            if not self.executed:
                self.executed = True
                return ("testname", "confname")
            raise QueueEmpty()

        successful_tests = []
        successful_subtests = []
        junit_tests = []
        tempest_report.utils.executer.return_value = (True, "")
        queue.get_nowait.side_effect = side_effect
        utils.worker(queue, successful_tests, successful_subtests, junit_tests)

        queue.get_nowait.assert_called_with()
        logger.assert_called_with('tempest_report')
        executer.assert_called_with('testname', "confname")
        self.assertEqual(successful_tests, ["testname"])
        self.assertEqual(len(junit_tests), 1)
        queue.task_done.assert_called_with()

    @mock.patch('keystoneclient.v2_0.client')
    @mock.patch('os.remove')
    @mock.patch('tempest_report.utils.customized_tempest_conf')
    @mock.patch('threading.Thread')
    @mock.patch('tempest_report.utils.logging')
    def test_main(self, logger, thread, customized_conf, remove, keystone):

        options = lambda: object
        options.os_username = "username"
        options.os_password = "password"
        options.os_auth_url = "auth_url"
        options.os_tenant_name = "tenant_name"
        options.fullrun = False
        options.level = 1
        options.max_release_level = 10
        options.verbose = False
        options.exclude = None
        options.junit = None
        options.is_admin = False

        thread.return_value.isAlive = lambda: False

        customized_conf.return_value = "dummy_content"
        with mock.patch(
            'tempest_report.settings.description_list',
                {'testname': {}}):

                utils.main(options)

        logger.getLogger().info.assert_any_call(
            '\nFailed tests:\ntestname')

        self.assertTrue(remove.called)
