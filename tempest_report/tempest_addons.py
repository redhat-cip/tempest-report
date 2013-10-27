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
        for line in self.cinder('list-extensions').split('\n'):
            res = m.search(line)
            if res:
                print "cinder-extension-%s ... ok" % res.group(1)


class NeutronExtensionTest(tempest.cli.ClientTestBase):
    def _get_extensions(self):
        if not hasattr(self, 'extensions'):
            self.extensions = self.neutron('ext-list')

    def test_security_group(self):
        self._get_extensions()
        self.assertIn("security-group", self.extensions)

    def test_l3_agent_scheduler(self):
        self._get_extensions()
        self.assertIn("l3_agent_scheduler", self.extensions)

    def test_ext_gw_mode(self):
        self._get_extensions()
        self.assertIn("ext-gw-mode", self.extensions)

    def test_binding(self):
        self._get_extensions()
        self.assertIn("binding", self.extensions)

    def test_quotas(self):
        self._get_extensions()
        self.assertIn("quotas", self.extensions)

    def test_agent(self):
        self._get_extensions()
        self.assertIn("agent", self.extensions)

    def test_dhcp_agent_scheduler(self):
        self._get_extensions()
        self.assertIn("dhcp_agent_scheduler", self.extensions)

    def test_multi_provider(self):
        self._get_extensions()
        self.assertIn("multi-provider", self.extensions)

    def test_external_net(self):
        self._get_extensions()
        self.assertIn("external-net", self.extensions)

    def test_router(self):
        self._get_extensions()
        self.assertIn("router", self.extensions)

    def test_allowed_address_pairs(self):
        self._get_extensions()
        self.assertIn("allowed-address-pairs", self.extensions)

    def test_extra_dhcp_opt(self):
        self._get_extensions()
        self.assertIn("extra_dhcp_opt", self.extensions)

    def test_provider(self):
        self._get_extensions()
        self.assertIn("provider", self.extensions)

    def test_extraroute(self):
        self._get_extensions()
        self.assertIn("extraroute", self.extensions)


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
