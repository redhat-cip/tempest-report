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

import json
import re
import requests

from keystoneclient.generic import client
import ceilometerclient.client
import tempest.api.image.base
import tempest.api.compute.base
import tempest.cli

try:
       from tempest.api.compute.base import BaseV2ComputeTest as BaseComputeTest
except ImportError:
       from tempest.api.compute.base import BaseComputeTest as BaseComputeTest


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


class NovaExtensionTest(BaseComputeTest):
    _interface = 'json'

    def test_extensions(self):
        _resp, ext = self.extensions_client.list_extensions()
        for ext in ext['extensions']:
            print "nova-extension-%s ... ok" % ext.get('alias')
        self.assertTrue(ext)

    def tearDown(self):
        super(NovaExtensionTest, self).tearDown()
        self.clear_servers()


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
    def test_meters(self):
        ceilo = ceilometerclient.client.get_client(1, **({
            'os_username': self.config.identity.username,
            'os_password': self.config.identity.password,
            'os_auth_url': self.config.identity.uri,
            'os_tenant_name': self.config.identity.tenant_name,
            }))
        for meter in ceilo.meters.list():
            print "ceilometer-meter-%s ... ok" % meter.name
        self.assertTrue(ceilo)

class KeystoneExtensionTest(tempest.cli.ClientTestBase):
    def _get_extensions(self, url):
        root = client.Client(url)
        extensions = root.discover_extensions(url)
        if extensions:
            for key, value in extensions.items():
                print "keystone-extension-%s ... ok" % key

    def test_keystone_admin(self):
        url = self.config.identity.uri + '/extensions'
        url = url.replace('5000', '35357')
        self._get_extensions(url)

    def test_keystone_user(self):
        self._get_extensions(self.config.identity.uri)
