# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>

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


class NovaExtensionTest(tempest.api.compute.base.BaseComputeTest):
    _interface = 'json'

    def _get_extensions(self):
        if not hasattr(self, 'extensions'):
            _resp, ext = self.extensions_client.list_extensions()
            self.extensions = []
            for e in ext['extensions']:
                self.extensions.append(e.get('alias'))

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


class CinderExtensionTest(tempest.cli.ClientTestBase):
    def _get_extensions(self):
        if not hasattr(self, 'extensions'):
            self.extensions = self.cinder('list-extensions')

    def test_os_extended_snapshot_attributes(self):
        self._get_extensions()
        self.assertIn("os-extended-snapshot-attributes", self.extensions)

    def test_os_admin_actions(self):
        self._get_extensions()
        self.assertIn("os-admin-actions", self.extensions)

    def test_os_availability_zone(self):
        self._get_extensions()
        self.assertIn("os-availability-zone", self.extensions)

    def test_backups(self):
        self._get_extensions()
        self.assertIn("backups", self.extensions)

    def test_os_image_create(self):
        self._get_extensions()
        self.assertIn("os-image-create", self.extensions)

    def test_os_hosts(self):
        self._get_extensions()
        self.assertIn("os-hosts", self.extensions)

    def test_qos_specs(self):
        self._get_extensions()
        self.assertIn("qos-specs", self.extensions)

    def test_os_quota_class_sets(self):
        self._get_extensions()
        self.assertIn("os-quota-class-sets ", self.extensions)

    def test_os_quota_sets(self):
        self._get_extensions()
        self.assertIn("os-quota-sets", self.extensions)

    def test_OS_SCH_HNT(self):
        self._get_extensions()
        self.assertIn("OS-SCH-HNT  ", self.extensions)

    def test_os_services(self):
        self._get_extensions()
        self.assertIn("os-services", self.extensions)

    def test_os_snapshot_actions(self):
        self._get_extensions()
        self.assertIn("os-snapshot-actions", self.extensions)

    def test_os_types_extra_specs(self):
        self._get_extensions()
        self.assertIn("os-types-extra-specs", self.extensions)

    def test_os_types_manage(self):
        self._get_extensions()
        self.assertIn("os-types-manage", self.extensions)

    def test_os_vol_mig_status_attr(self):
        self._get_extensions()
        self.assertIn("os-vol-mig-status-attr", self.extensions)

    def test_os_volume_transfer(self):
        self._get_extensions()
        self.assertIn("os-volume-transfer", self.extensions)

    def test_os_vol_image_meta(self):
        self._get_extensions()
        self.assertIn("os-vol-image-meta", self.extensions)

    def test_encryption(self):
        self._get_extensions()
        self.assertIn("encryption", self.extensions)


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
