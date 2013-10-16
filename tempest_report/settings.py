# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>

# mapping of tests to openstack versions
name_mapping = {
    5: 'Essex',
    6: 'Folsom',
    7: 'Grizzly',
    8: 'Havana',
    9: 'Icehouse',
}

description_list = {
    # Minimal tests that don't require an admin account
    'tempest.cli.simple_read_only.test_keystone:SimpleReadOnlyKeystoneClientTest.test_admin_discover': {
        'service': 'Identity Service (Keystone)',
        'feature': '',
        'release': 0,
    },

    'tempest.cli.simple_read_only.test_glance:SimpleReadOnlyGlanceClientTest.test_glance_image_list': {
        'service': 'Image Service (Glance)',
        'feature': '',
        'release': 0,
    },

    'tempest.cli.simple_read_only.test_compute:SimpleReadOnlyNovaClientTest.test_admin_list': {
        'service': 'Compute (Nova)',
        'feature': '',
        'release': 0,
    },

    'tempest.cli.simple_read_only.test_cinder:SimpleReadOnlyCinderClientTest.test_cinder_volumes_list': {
        'service': 'Volume Service (Cinder)',
        'feature': '',
        'release': 0,
    },
    
    'tempest.api.object_storage.test_container_services:ContainerTest.test_create_container': {
        'service': 'Object Storage (Swift)',
        'feature': '',
        'release': 0,
    },

    # End of minimal tests

    # Additional tests for feature / release detection

    # Swift tests

    'tempest.api.object_storage.test_container_quotas': {
        'service': 'Object Storage (Swift)',
        'feature': 'Container Quota',
        'release': 7,
    },

    'tempest.api.object_storage.test_object_expiry': {
        'service': 'Object Storage (Swift)',
        'feature': 'Expiring Objects',
        'release': 5,
    },
    
    'tempest.api.object_storage.test_object_version': {
        'service': 'Object Storage (Swift)',
        'feature': 'Object versioning',
        'release': 6,
    }, 

    'tempest.api.object_storage.test_object_temp_url:ObjectTempUrlTest.test_get_object_using_temp_url': {
        'service': 'Object Storage (Swift)',
        'feature': 'Temporary object URL',
        'release': 5,
    },

    'tempest.api.object_storage.test_container_sync': {
        'service': 'Object Storage (Swift)',
        'feature': 'Container sync',
        'release': 6,
    },

    'tempest.api.object_storage.test_container_staticweb': {
        'service': 'Object Storage (Swift)',
        'feature': 'Static Web',
        'release': 0,
    },


    # Nova tests
   
    'tempest_report.tempest_addons:NovaExtensionTest.test_volume_support': {
        'service': 'Compute (Nova)',
        'feature': 'Volume Support',
        'release': 0,
    },

    'tempest_report.tempest_addons:NovaExtensionTest.test_multinic': {
        'service': 'Compute (Nova)',
        'feature': 'Multi-NIC Support',
        'release': 5,
    },

    'tempest_report.tempest_addons:NovaExtensionTest.test_server_password': {
        'service': 'Compute (Nova)',
        'feature': 'Server password support',
        'release': 7,
    },
 
    'tempest_report.tempest_addons:NovaExtensionTest.test_extended_status': {
        'service': 'Compute (Nova)',
        'feature': 'Extended Status support',
        'release': 5,
    },

    'tempest_report.tempest_addons:NovaExtensionTest.test_user_data': {
        'service': 'Compute (Nova)',
        'feature': 'User Data support',
        'release': 6,
    },

    # Glance

    'tempest_report.tempest_addons:GlanceTest': {
        'service': 'Image Service (Glance)',
        'feature': '',
        'release': 6,
    },

}
