# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>

import re

import ceilometerclient.client
import tempest.api.image.base
import tempest.api.compute.base
import tempest.cli


class GlanceV2Test(tempest.api.image.base.BaseV2ImageTest):

    def test_list_images(self):
        resp, images_list = self.client.image_list()
        self.assertEqual(resp['status'], '200')
        self.assertTrue(len(images_list) > 0)


class GlanceV1Test(tempest.api.image.base.BaseV1ImageTest):

    def test_list_images(self):
        resp, images_list = self.client.image_list()
        self.assertEqual(resp['status'], '200')
        self.assertTrue(len(images_list) > 0)


class NovaExtensionTest(tempest.api.compute.base.BaseV2ComputeTest):
    _interface = 'json'

    def test_extensions(self):
        _resp, ext = self.extensions_client.list_extensions()
        for ext in ext['extensions']:
            print "nova-extension-%s ... ok" % ext.get('alias')
        self.assertTrue(ext)


class CinderExtensionTest(tempest.cli.ClientTestBase):
    def test_extensions(self):
        m = re.compile('\|.*\|.*\|\s+([A-Za-z-]*)\s+\|.*\|')
        extensions = self.cinder('list-extensions').split('\n')
        for line in extensions:
            res = m.search(line)
            if res:
                print "cinder-extension-%s ... ok" % res.group(1)
        self.assertTrue(extensions)


class NeutronExtensionTest(tempest.cli.ClientTestBase):
    def test_extensions(self):
        m = re.compile('\|\s+([A-Za-z-]*)\s+\|.*\|')
        extensions = self.neutron('ext-list').split('\n')
        for line in extensions:
            res = m.search(line)
            if res:
                print "neutron-extension-%s ... ok" % res.group(1)
        self.assertTrue(extensions)


class CeilometerTest(tempest.cli.ClientTestBase):
    def _get_meters(self):
        if not hasattr(self, 'meters'):
            ceilo = ceilometerclient.client.get_client(1, **({
                'os_username': self.config.identity.username,
                'os_password': self.config.identity.password,
                'os_auth_url': self.config.identity.uri,
                'os_tenant_name': self.config.identity.tenant_name,
                }))
            self.meters = []
            for meter in ceilo.meters.list():
                self.meters.append(meter.name)

    def test_meter_disk(self):
        self._get_meters()
        self.assertIn("storage.api.request", self.meters)

    def test_meter_objectstorage(self):
        self._get_meters()
        self.assertIn("storage.objects", self.meters)

    def test_meter_network(self):
        self._get_meters()
        self.assertIn("network", self.meters)

    def test_meter_subnet(self):
        self._get_meters()
        self.assertIn("subnet", self.meters)

    def test_meter_router(self):
        self._get_meters()
        self.assertIn("router", self.meters)
