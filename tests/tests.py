# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>

#pylint: disable=E1101, E1103

import subprocess
import unittest

import mock
import keystoneclient
import glanceclient

from tempest_report import utils, settings


class DummyFileObject(object):
    def __init__(self, *_args, **_kwargs):
        self.name = '/dir/dummy'
        self.content = None

    def __exit__(self, *_args, **_kwargs):
        pass

    def __enter__(self, *_args, **_kwargs):
        pass

    def write(self, content, *_args, **_kwargs):
        self.content = content


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
            self.assertEqual(release_name, 'Essex')

    def test_summary_class(self):
        summary = utils.ServiceSummary('servicename')
        self.assertEqual(summary.release_name, '')
        
        summary.set_release(5)
        self.assertEqual(summary.release_name, 'Essex')

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
   
    # TODO
    def test_customized_tempest_conf(self):
    	pass    
