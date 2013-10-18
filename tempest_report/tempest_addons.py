# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>

import tempest.api.image.base
import tempest.api.compute.base
from tempest.test import attr


class NovaExtensionTest(tempest.api.compute.base.BaseComputeTest):
    _interface = 'json'
    
    def _get_extensions(self):
        if not hasattr(self, 'extensions'):
            _resp, ext = self.extensions_client.list_extensions()
            self.extensions = []
            for e in ext['extensions']:
                print e
                self.extensions.append(e.get('alias'))

    def test_server_password(self):
        self._get_extensions()
        self.assertIn("os-server-password", self.extensions)

    def test_volume_support(self):
        self._get_extensions()
        self.assertIn("os-volumes", self.extensions)

    def test_multinic(self):
        self._get_extensions()
        self.assertIn("NMN", self.extensions)

    def test_extended_status(self):
        self._get_extensions()
        self.assertIn("OS-EXT-STS", self.extensions)

    def test_user_data(self):
        self._get_extensions()
        self.assertIn("os-user-data", self.extensions)


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
