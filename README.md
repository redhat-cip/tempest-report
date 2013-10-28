# tempest-report

tempest-report is a tool for OpenStack Tempest to test remote installations and summarize found services and extensions.

Installation
------------

1) Install requirements

Using a fresh Ubuntu Server (12.0.4 LTS) installation you need to install these packages:

    sudo apt-get install python-pip git python-greenlet python-openssl python-crypto python-lxml

2) Clone repository

    git clone https://github.com/enovance/tempest-report.git
    cd tempest-report

3) Install requirements

    sudo pip install -r requirements.txt

4) Install tempest_report

    sudo python setup.py install


Usage
---------

1) Create a file "tempest.env" with these environment variables (you can also use the command line switches, but this will show up in your shell history):

    export OS_USERNAME=demo
    export OS_PASSWORD=devstack
    export OS_AUTH_URL=http://127.0.0.1:5000/v2.0/

2) Run basic tests:

    $ source tempest.env
    $ tempest_report

    Failed tests:
    tempest.api.object_storage.test_object_version
    
    Successful tests:
    tempest_report.tempest_addons:NovaExtensionTest.test_server_password
    tempest_report.tempest_addons:GlanceV1Test
    tempest.api.object_storage.test_object_temp_url:ObjectTempUrlTest.test_get_object_using_temp_url
    tempest.cli.simple_read_only.test_keystone:SimpleReadOnlyKeystoneClientTest.test_admin_discover
    tempest.thirdparty.boto.test_s3_buckets
    tempest_report.tempest_addons:NovaExtensionTest.test_volume_support
    tempest_report.tempest_addons:GlanceV2Test
    tempest.api.object_storage.test_container_quotas
    tempest_report.tempest_addons:NovaExtensionTest.test_user_data
    tempest.api.object_storage.test_object_expiry
    tempest.thirdparty.boto.test_ec2_instance_run
    tempest.api.object_storage.test_container_staticweb
    tempest_report.tempest_addons:NovaExtensionTest.test_multinic
    tempest.api.object_storage.test_container_services
    tempest_report.tempest_addons:NovaExtensionTest.test_extended_status
    tempest.cli.simple_read_only.test_glance:SimpleReadOnlyGlanceClientTest.test_glance_image_list
    tempest.api.object_storage.test_container_sync
    tempest.cli.simple_read_only.test_nova_manage
    tempest.cli.simple_read_only.test_cinder:SimpleReadOnlyCinderClientTest.test_cinder_volumes_list
    tempest.api.object_storage.test_container_services:ContainerTest.test_create_container
    
    Identity Service (Keystone): 
    Compute (Nova): Grizzly
    				Server password support
    				Volume Support
    				User Data support
    				EC2 API
    				Multi-NIC Support
    				Extended Status support
    Image Service (Glance): Folsom
    				V1 Api
    				V2 Api
    Object Storage (Swift): Grizzly
    				Temporary object URL
    				S3 API
    				Container Quota
    				Static Web
    Volume Service (Cinder): 


Testing
-------

    nosetests --with-coverage --cover-package=tempest_report
