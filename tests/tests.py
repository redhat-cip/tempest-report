# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>

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


class KeystoneDummy(object):
    class Tenants(object):
        def findall(self):
            tenant = Tenant()
            return [tenant]

    def __init__(self, *_args, **_kwargs):
        self.auth_ref = {'token': {'id': 'token'}, 
                         'serviceCatalog': [{
                             'type': 'servicetype',
                             'endpoints': [{
                                 'publicURL': 'url'
                            }],
                        }]}
        self.tenants = self.Tenants()

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
        services, scoped_token = utils.get_services("tenant_name",
            "token_id", "http://127.0.0.1:5000", KeystoneDummy)

        self.assertEqual(services, {'servicetype': 'url'})
        self.assertEqual(scoped_token, {'id': 'token'})

    @mock.patch('keystoneclient.v2_0.client')
    def test_get_tenants(self, keystone):
        tenants, token = utils.get_tenants("user",
                "password", "http://127.0.0.1:5000", KeystoneDummy)

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
            ["nosetests", "-v", "testname"],
            stderr=subprocess.STDOUT)
        
        subprocess_mock.side_effect = subprocess.CalledProcessError(
            1, "command", "error")
        success, output = utils.executer(
            "testname", "filename")
    
        self.assertFalse(success)
        self.assertEqual(output, "error")

    def test_summary(self):
        dscr = {
            'test.a' : {'service': 'A',
                        'feature': '1',
                        'release': 0},
            'test.b' : {'service': 'B',
                        'feature': '2',
                        'release': 5},
            }

        with mock.patch.dict(settings.description_list, dscr):
            
            successful_tests = ['test.a', 'test.b']
            summary = utils.service_summary(successful_tests)
            
            assert 'A' in summary
            assert '1' in summary.get('A').features
            assert 'B' in summary
            assert '2' in summary.get('B').features
            release_name = summary.get('B').release_name
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

        retval = utils.get_images("token_id", "http://url:5000/v2")
        self.assertEqual(retval, ['first image'])

        glance.assert_called_with(2, "http://url:5000", 
        token="token_id")

        self.raised = False
        def side_effect(*args, **kwargs):
            if not self.raised:
                self.raised = True
                raise glanceclient.exc.HTTPNotFound()
            return glance
 
        glance.side_effect = side_effect
 
        utils.get_images("token_id", "http://url:5000/v2")

        glance.assert_called_with(1, "http://url:5000",
        token="token_id")

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

    @mock.patch('keystoneclient.generic.client.Client')
    def test_get_keystone_client_v2(self, keystone):
        keystone.return_value = KeystoneDummy()

        client, url = utils.get_keystone_client('http://127.0.0.1:5000')
        self.assertEqual(client, keystoneclient.v2_0.client.Client)
        self.assertEqual(url, 'http://127.0.0.1:5000/v2')

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
   
    @mock.patch('tempest_report.utils.get_keystone_client')
    @mock.patch('tempest_report.utils.get_tenants')
    @mock.patch('tempest_report.utils.get_services')
    @mock.patch('tempest_report.utils.get_flavors')
    @mock.patch('tempest_report.utils.get_images')
    @mock.patch('tempest_report.utils.write_conf')
    def test_customized_tempest_conf(self,
        get_keystone_client, get_tenants, get_services,
        get_flavors, get_images, write_conf):
        
        tempest_report.utils.get_keystone_client.return_value = (
            None, 'keystone_url')
        
        class ObjDummy(object):
            pass
        
        tenant = ObjDummy()
        tenant.name = "tenant_name"
        tempest_report.utils.get_tenants.return_value = (
            [tenant], None)
       
        image = ObjDummy()
        image.size = 1
        image.id = 23
        tempest_report.utils.get_images.return_value = (
            [image])

        flavor = ObjDummy()
        flavor.vcpus = 1
        flavor.disk = 1
        flavor.ram = 1
        flavor.id = 42
        tempest_report.utils.get_flavors.return_value = (
            [flavor])

        tempest_report.utils.get_services.return_value = (
            {'image': 'url'}, {'id': 'id'})

        fileobj = mock.Mock()
        utils.customized_tempest_conf("user", "password",
            "http://keystone_url", fileobj)

        tempest_report.utils.write_conf.assert_called_with(
            'user', 'password', 'keystone_url', 
            'tenant_name', 23, 42, fileobj, 
            {'image': 'url'})

    def test_write_conf(self):

        fileobj = DummyFileObject()
        utils.write_conf("user", "password", "keystone_url", "tenant",
                         "image_id", "flavor_id", fileobj, {'compute': 'url'})
        
        self.assertIn("[DEFAULT]", fileobj.content)
        self.assertIn("use_stderr = False", fileobj.content)
        self.assertIn("log_file = tempest.log", fileobj.content)
        self.assertIn("[stress]", fileobj.content)
        self.assertIn("[compute]", fileobj.content)
        self.assertIn("image_ref = image_id", fileobj.content)
        self.assertIn("image_ref_alt = image_id", fileobj.content)
        self.assertIn("allow_tenant_isolation = False", fileobj.content)
        self.assertIn("flavor_ref = flavor_id", fileobj.content)
        self.assertIn("flavor_ref_alt = flavor_id", fileobj.content)
        self.assertIn("[network]", fileobj.content)
        self.assertIn("[boto]", fileobj.content)
        self.assertIn("[scenario]", fileobj.content)
        self.assertIn("[object_storage]", fileobj.content)
        self.assertIn("operator_role = tenant", fileobj.content)
        self.assertIn("[volume]", fileobj.content)
        self.assertIn("[debug]", fileobj.content)
        self.assertIn("[dashboard]", fileobj.content)
        self.assertIn("[orchestration]", fileobj.content)
        self.assertIn("[compute_admin]", fileobj.content)
        self.assertIn("[images]", fileobj.content)
        self.assertIn("[service_available]", fileobj.content)
        self.assertIn("cinder = False", fileobj.content)
        self.assertIn("glance = False", fileobj.content)
        self.assertIn("swift = False", fileobj.content)
        self.assertIn("nova = True", fileobj.content)
        self.assertIn("neutron = False", fileobj.content)
        self.assertIn("[identity]", fileobj.content)
        self.assertIn("uri = keystone_url", fileobj.content)
        self.assertIn("username = user", fileobj.content)
        self.assertIn("alt_username = user", fileobj.content)
        self.assertIn("admin_username = user", fileobj.content)
        self.assertIn("password = password", fileobj.content)
        self.assertIn("alt_password = password", fileobj.content)
        self.assertIn("admin_password = password", fileobj.content)
        self.assertIn("tenant_name = tenant", fileobj.content)
        self.assertIn("alt_tenant_name = tenant", fileobj.content)
        self.assertIn("admin_tenant_name = tenant", fileobj.content)
        self.assertIn("admin_role = tenant", fileobj.content)

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
        tempest_report.utils.executer.return_value = (True, "")
        queue.get_nowait.side_effect = side_effect 
        utils.worker(queue, successful_tests)

        queue.get_nowait.assert_called_with()
        logger.assert_called_with('tempest_report')
        executer.assert_called_with('testname', "confname")
        self.assertEqual(successful_tests, ["testname"])
        queue.task_done.assert_called_with()

    @mock.patch('os.remove')
    @mock.patch('tempest_report.utils.customized_tempest_conf')
    @mock.patch('threading.Thread')
    @mock.patch('tempest_report.utils.logging')
    def test_main(self, logger, thread, customized_conf, remove):
        
        options = lambda: object
        options.os_username = "username"
        options.os_password = "password"
        options.os_auth_url = "auth_url"
        options.os_tenant_name = "tenant_name"
        options.fullrun = False 
        options.level = 1
        options.max_release_level = 10
        options.verbose = False

        thread.return_value.isAlive = lambda: False
        
        with mock.patch(
            'tempest_report.settings.description_list',
            {'testname': {}}):
            utils.main(options)
        
        logger.getLogger().info.assert_any_call(
            '\nFailed tests:\ntestname')
        
        self.assertTrue(remove.called)
