# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>

#pylint: disable=E1101, E1103

from tempest_report import utils, settings

import unittest
import tempfile

import mock
import subprocess
import ConfigParser

from tempest_report.utils import customized_tempest_conf, get_smallest_flavor, get_smallest_image, get_services, get_tenants, ServiceSummary, service_summary, executer, get_images, get_flavors


from keystoneclient.v2_0 import client 
import glanceclient
import novaclient
import requests


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


class KeystoneDummy(object):
    def __init__(self, *_args, **_kwargs):
        self.auth_ref = {'token': {'id': 'token'}, 
                         'serviceCatalog': [{
                             'type': 'servicetype',
                             'endpoints': [{
                                 'publicURL': 'url'
                            }],
                        }]}


class UtilTest(unittest.TestCase):
    def test_customized_tempest_conf(self):
        class DummyObj(object):
            def __init__(self, id, *args, **kwargs):
                self.id = id

        utils.get_tenants = mock.Mock(return_value=(
            [{'id': 'tenant_id', 'name': 'tenant_name'}, ], 
            'token'))
        utils.get_services = mock.Mock(return_value=
            ({'identity': 'none'}, 'scoped_token'))
        
        flv_obj = DummyObj("42")
        utils.get_smallest_flavor = mock.Mock(return_value=flv_obj)
        img_obj = DummyObj("image-uuid")
        utils.get_smallest_image = mock.Mock(return_value=img_obj)
        fileobj = DummyFileObject()
        retval = customized_tempest_conf('user', 'password', 'url', fileobj)
        
        # TODO: check if config is valid

    
    def test_get_smallest_flavor(self):
        class DummyFlavor(object):
            def __init__(self, vcpus, disk, ram, *args, **kwargs):
                self.vcpus = vcpus
                self.disk = disk
                self.ram = ram

        sample_flavors = []
        sample_flavors.append(DummyFlavor(1, 1, 128))
        sample_flavors.append(DummyFlavor(1, 0, 64))
        sample_flavors.append(DummyFlavor(1, 1, 64))

        utils.get_flavors = mock.Mock(return_value=sample_flavors)
        smallest_flavor = get_smallest_flavor(0, 0, 0, 0)
        self.assertEqual(smallest_flavor.disk, 0)

    def test_get_smallest_image(self):
        class DummyImage(object):
            def __init__(self, size, disk_format, status, *args, **kwargs):
                self.size = size
                self.disk_format = disk_format
                self.status = status

        utils.get_tenants = mock.Mock(return_value=
            ([{'name': 'tenant_name'}], 'token'))
        utils.get_services = mock.Mock(return_value=
            ({'image': 'url'}, {'id': 'scoped_token'}))

        sample_images = []
        sample_images.append(DummyImage(10, 'qcow2', 'active'))
        sample_images.append(DummyImage(2, 'qcow2', 'active'))
        sample_images.append(DummyImage(1, 'other', 'active'))
        sample_images.append(DummyImage(1, 'qcow2', 'other'))

        utils.get_images = mock.Mock(return_value=sample_images)
        smallest_image = get_smallest_image(0, 0, 0)
        self.assertEqual(smallest_image.size, 2)

    def test_get_services(self):
        client.Client = mock.Mock(return_value=KeystoneDummy())
        services, scoped_token = get_services("tenant_name",
            "token_id", "keystone_url")
        self.assertEqual(services, {'servicetype': 'url'})
        self.assertEqual(scoped_token, {'id': 'token'})
        client.Client.assert_called_with(auth_url="keystone_url",
            token="token_id", tenant_name="tenant_name")

    def test_get_tenants(self):
        class DummyResponse(object):
            def json(self, *_args, **_kwargs):
                return {'tenants': 'tenants'}

        client.Client = mock.Mock(return_value=KeystoneDummy())
        requests.get = mock.Mock(return_value=DummyResponse())
        
        tenants, token = get_tenants("user",
            "password", "keystone_url")
        
        self.assertEqual(tenants, 'tenants')
        self.assertEqual(token, 'token')
        client.Client.assert_called_with(username="user",
            password="password", auth_url="keystone_url")

    def test_executer(self):
        subprocess.check_output=mock.Mock(return_value="output") 
        success, output = executer("testname", "/dir/filename")
        
        self.assertTrue(success)
        self.assertEqual(output, "output")
        subprocess.check_output.assert_called_with(
            ["nosetests", "-v", "testname"], stderr=subprocess.STDOUT)

        subprocess.check_output=mock.Mock(return_value="output")
        subprocess.check_output.side_effect = \
            subprocess.CalledProcessError(1, "command", "error")
        success, output = executer("testname", "filename")
        
        self.assertFalse(success)
        self.assertEqual(output, "error")

    def test_summary(self):
        successful_tests = ['test.a', 'test.b']
        with mock.patch.dict(settings.description_list, {
            'test.a' : {'service': 'A',
                        'feature': '1',
                        'release': 0},
            'test.b' : {'service': 'B',
                        'feature': '2',
                        'release': 5},
            }):
            
            summary = service_summary(successful_tests)
            
            assert 'A' in summary
            assert '1' in summary.get('A').features
            assert 'B' in summary
            assert '2' in summary.get('B').features
            self.assertEqual(summary.get('B').release_name, 'Essex')

    def test_summary_class(self):
        summary = ServiceSummary('servicename')
        self.assertEqual(summary.release_name, '')
        
        summary.set_release(5)
        self.assertEqual(summary.release_name, 'Essex')

        summary.set_release(999)
        self.assertEqual(summary.release_name, '')

        summary.add_feature('feature')
        summary.add_feature('feature')

        self.assertEqual(str(summary), 'servicename')
        self.assertEqual(summary.features, ['feature', ])

    def test_get_images(self):
        class DummyImages(object):
            def list(self):
                return ['first image']

        with mock.patch('glanceclient.Client') as glance:
            images = DummyImages()
            glance.return_value.images = images
            retval = get_images("token_id", "http://url:5000/v2")
            self.assertEqual(retval, ['first image'])

        glance.assert_called_with(2, "http://url:5000", 
            token="token_id")
        
        with mock.patch('glanceclient.Client') as glance:
            get_images("token_id", "http://url:35357/v1")

        glance.assert_called_with(1, "http://url:35357",
            token="token_id")

        with mock.patch('glanceclient.Client') as glance:
            get_images("token_id", "http://url/wrong")

        glance.assert_called_with(1, "http://url",
            token="token_id")

    def test_get_flavors(self):
        class DummyFlavors(object):
            def list(self):
                return ['flavor']

        with mock.patch('novaclient.v1_1.client.Client') as nova:
            flavors = DummyFlavors()
            nova.return_value.flavors = flavors
            retval = get_flavors("user", "password",
                "tenant_name", "url")
            self.assertEqual(retval, ['flavor'])

        nova.assert_called_with("user", "password",
            "tenant_name", "url")
