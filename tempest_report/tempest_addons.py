# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>

import tempest.api.image.base
import tempest.api.compute.base
from tempest.test import attr


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


class NovaExtensionTest(tempest.api.compute.base.BaseComputeTest):
    _interface = 'json'
    
    def _get_extensions(self):
        if not hasattr(self, 'extensions'):
            _resp, ext = self.extensions_client.list_extensions()
            self.extensions = []
            for e in ext['extensions']:
                self.extensions.append(e.get('alias'))
		testname = e['alias'].replace('-', '_')
		#print '    def test_%s(self):' % testname
        	#print '        self._get_extensions()'
        	#print '        self.assertIn("%s", self.extensions)\n' % e['alias']
		print "tempest_report.tempest_addons:NovaExtensionTest.test_%s': {'service': 'Compute (Nova)', 'feature': '%s', }," % (testname, e['description'])
    
    def test_dummy(self):
        self._get_extensions()

    def test_NMN(self):
        self._get_extensions()
        self.assertIn("NMN", self.extensions)

    def test_OS_DCF(self):
        self._get_extensions()
        self.assertIn("OS-DCF", self.extensions)

    def test_OS_EXT_AZ(self):
        self._get_extensions()
        self.assertIn("OS-EXT-AZ", self.extensions)

    def test_OS_EXT_SRV_ATTR(self):
        self._get_extensions()
        self.assertIn("OS-EXT-SRV-ATTR", self.extensions)

    def test_OS_EXT_STS(self):
        self._get_extensions()
        self.assertIn("OS-EXT-STS", self.extensions)

    def test_os_assisted_volume_snapshots(self):
        self._get_extensions()
        self.assertIn("os-assisted-volume-snapshots", self.extensions)

    def test_os_create_server_ext(self):
        self._get_extensions()
        self.assertIn("os-create-server-ext", self.extensions)

    def test_os_deferred_delete(self):
        self._get_extensions()
        self.assertIn("os-deferred-delete", self.extensions)

    def test_os_extended_volumes(self):
        self._get_extensions()
        self.assertIn("os-extended-volumes", self.extensions)

    def test_os_fixed_ips(self):
        self._get_extensions()
        self.assertIn("os-fixed-ips", self.extensions)

    def test_os_flavor_access(self):
        self._get_extensions()
        self.assertIn("os-flavor-access", self.extensions)

    def test_os_floating_ip_dns(self):
        self._get_extensions()
        self.assertIn("os-floating-ip-dns", self.extensions)

    def test_os_floating_ip_pools(self):
        self._get_extensions()
        self.assertIn("os-floating-ip-pools", self.extensions)

    def test_os_floating_ips(self):
        self._get_extensions()
        self.assertIn("os-floating-ips", self.extensions)

    def test_os_rescue(self):
        self._get_extensions()
        self.assertIn("os-rescue", self.extensions)

    def test_os_security_groups(self):
        self._get_extensions()
        self.assertIn("os-security-groups", self.extensions)

    def test_os_server_password(self):
        self._get_extensions()
        self.assertIn("os-server-password", self.extensions)

    def test_os_shelve(self):
        self._get_extensions()
        self.assertIn("os-shelve", self.extensions)

    def test_os_user_quotas(self):
        self._get_extensions()
        self.assertIn("os-user-quotas", self.extensions)

    def test_os_virtual_interfaces(self):
        self._get_extensions()
        self.assertIn("os-virtual-interfaces", self.extensions)

    def test_os_volumes(self):
        self._get_extensions()
        self.assertIn("os-volumes", self.extensions)

    def test_user_data(self):
        self._get_extensions()
        self.assertIn("os-user-data", self.extensions)


