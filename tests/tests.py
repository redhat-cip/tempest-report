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
import keystoneclient
import glanceclient

from tempest_report import utils, settings
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


class Tenant(object):
    def __init__(self):
        self.name = "Tenant Name"
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
    def test_get_smallest_flavor(self):
        class DummyFlavor(object):
            def __init__(self, vcpus, disk, ram):
                self.vcpus = vcpus
                self.disk = disk
                self.ram = ram

        sample_flavors = []
        sample_flavors.append(DummyFlavor(1, 1, 128))
        sample_flavors.append(DummyFlavor(1, 0, 64))
        sample_flavors.append(DummyFlavor(1, 1, 64))

        smallest_flavor = utils.get_smallest_flavor(sample_flavors)
        self.assertEqual(smallest_flavor.disk, 0)

    @mock.patch('keystoneclient.v2_0.client')
    def test_get_services(self, keystone):
        keystone.Client = KeystoneDummy
        services, scoped_token = utils.get_services("user",
                                                    "password",
                                                    "tenant_name",
                                                    "http://127.0.0.1:5000")

        self.assertEqual(services, {'servicetype': 'url'})
        self.assertEqual(scoped_token, {'id': 'token'})

    @mock.patch('keystoneclient.v2_0.client')
    def test_get_tenants(self, keystone):
        keystone.Client = KeystoneDummy
        tenants, token = utils.get_tenants("user",
                                           "password",
                                           "http://127.0.0.1:5000")
        self.assertTrue(isinstance(tenants[0], Tenant))
        self.assertEqual(token, 'token')

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

    @mock.patch('glanceclient.Client')
    def test_get_images(self, glance):
        class DummyImages(object):
            def list(self):
                return ['first image']

        images = DummyImages()
        glance.return_value.images = images

        services = {'image': 'http://url:5000'}
        token = {'id': 'token_id'}

        retval = utils.get_images(services, token)
        self.assertEqual(retval, ['first image'])

        glance.assert_called_with(2, "http://url:5000", token="token_id")

        self.raised = False

        def side_effect(*args, **kwargs):
            if not self.raised:
                self.raised = True
                raise glanceclient.exc.HTTPNotFound()
            return glance

        glance.side_effect = side_effect

        utils.get_images(services, token)

        glance.assert_called_with(1, "http://url:5000", token="token_id")

    @mock.patch('novaclient.v1_1.client.Client')
    def test_get_flavors(self, nova):
        class DummyFlavors(object):
            def list(self):
                return ['flavor']

        flavors = DummyFlavors()
        nova.return_value.flavors = flavors
        retval = utils.get_flavors("user", "password",
                                   "tenant_name", "url")
        self.assertEqual(retval, ['flavor'])

        nova.assert_called_with("user", "password",
                                "tenant_name", "url")

    def test_get_smallest_image(self):
        class DummyImage(object):
            def __init__(self, size, disk_format, status):
                self.size = size
                self.disk_format = disk_format
                self.status = status

        images = []
        images.append(DummyImage(10, 'qcow2', 'active'))
        images.append(DummyImage(2, 'qcow2', 'active'))
        images.append(DummyImage(1, 'other', 'active'))
        images.append(DummyImage(1, 'qcow2', 'other'))

        smallest_image = utils.get_smallest_image(images)
        self.assertEqual(smallest_image.size, 2)

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

    @mock.patch('keystoneclient.v2_0.client.Client')
    @mock.patch('tempest_report.utils.get_tenants')
    @mock.patch('tempest_report.utils.get_services')
    @mock.patch('tempest_report.utils.get_flavors')
    @mock.patch('tempest_report.utils.get_images')
    def test_customized_tempest_conf(self,
                                     get_tenants,
                                     get_services,
                                     get_flavors,
                                     get_images,
                                     keystone):

        class ObjDummy(object):
            pass

        tenant = ObjDummy()
        tenant.name = "tenant_name"
        tempest_report.utils.get_tenants.return_value = (
            [tenant], None)

        image = ObjDummy()
        image.size = 1
        image.id = "23"
        image.disk_format = "ami"
        image.status = "active"
        tempest_report.utils.get_images.return_value = (
            [image])

        flavor = ObjDummy()
        flavor.vcpus = 1
        flavor.disk = 1
        flavor.ram = 1
        flavor.id = "42"
        tempest_report.utils.get_flavors.return_value = (
            [flavor])

        tempest_report.utils.get_services.return_value = (
            {'image': 'url'}, {'id': 'id'})

        users = {'admin_user': {'username': 'user',
                                'password': 'password',
                                'tenant_name': 'tenant_name'},
                 'first_user': {'username': 'user',
                                'password': 'password',
                                'tenant_name': 'tenant_name'},
                 'second_user': {'username': 'user',
                                 'password': 'password',
                                 'tenant_name': 'tenant_name'}}

        content = utils.customized_tempest_conf(users, "http://keystone_url")

        self.assertIn("[DEFAULT]", content)
        self.assertIn("use_stderr = False", content)
        self.assertIn("log_file = tempest.log", content)
        self.assertIn("[stress]", content)
        self.assertIn("[compute]", content)
        self.assertIn("image_ref = 23", content)
        self.assertIn("image_ref_alt = 23", content)
        self.assertIn("allow_tenant_isolation = False", content)
        self.assertIn("flavor_ref = 42", content)
        self.assertIn("flavor_ref_alt = 42", content)
        self.assertIn("[network]", content)
        self.assertIn("[boto]", content)
        self.assertIn("[scenario]", content)
        self.assertIn("[object_storage]", content)
        self.assertIn("operator_role = tenant", content)
        self.assertIn("[volume]", content)
        self.assertIn("[debug]", content)
        self.assertIn("[dashboard]", content)
        self.assertIn("[orchestration]", content)
        self.assertIn("[compute_admin]", content)
        self.assertIn("[images]", content)
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
        self.assertIn("admin_username = user", content)
        self.assertIn("password = password", content)
        self.assertIn("alt_password = password", content)
        self.assertIn("admin_password = password", content)
        self.assertIn("tenant_name = tenant", content)
        self.assertIn("alt_tenant_name = tenant", content)
        self.assertIn("admin_tenant_name = tenant", content)
        self.assertIn("admin_role = tenant", content)

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
        tempest_report.utils.executer.return_value = (True, "")
        queue.get_nowait.side_effect = side_effect
        utils.worker(queue, successful_tests, successful_subtests)

        queue.get_nowait.assert_called_with()
        logger.assert_called_with('tempest_report')
        executer.assert_called_with('testname', "confname")
        self.assertEqual(successful_tests, ["testname"])
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
