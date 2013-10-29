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

2) Run basic extension and release discovery:

    $ source tempest.env
    $ tempest_report

    Failed tests:
    tempest.api.object_storage.test_container_sync
    
    Successful tests:
    tempest_report.tempest_addons:NeutronExtensionTest
    tempest_report.tempest_addons:NovaExtensionTest
    tempest_report.tempest_addons:GlanceV1Test
    tempest.api.object_storage.test_object_expiry
    tempest.cli.simple_read_only.test_glance:SimpleReadOnlyGlanceClientTest.test_glance_image_list
    tempest_report.tempest_addons:CeilometerTest
    tempest.api.object_storage.test_container_staticweb
    tempest.api.object_storage.test_object_version
    tempest_report.tempest_addons:GlanceV2Test
    tempest.api.object_storage.test_object_temp_url:ObjectTempUrlTest.test_get_object_using_temp_url
    tempest.api.object_storage.test_container_quotas
    tempest_report.tempest_addons:CinderExtensionTest
    tempest.scenario.test_dashboard_basic_ops
    
    Network (Neutron): Havana (or later)
    				Neutron L3 Configurable external gateway mode
                    
                    [... shortened list ...]
    				
                    Quota management support
    
    Scenario: 
    				Dashboard (Horizon)
    
    Compute (Nova): Havana (or later)
    				Multinic
                    
                    [... shortened list ...]
    				
    				Volumes
    
    Metering (Ceilometer): 
    				Disk Usage
    
    Object Storage (Swift): Grizzly (or later)
    				Object expiring
    				Static Web
    				Object versioning
    				Temporary object URL
    				Container Quota
    
    Image (Cinder): Havana (or later)
    				Enable admin actions
    				
                    [... shortened list ...]
                    
                    Volume encryption
    
    Volume (Glance): Folsom (or later)
    				V1 Api
    				V2 Api


You can increase the test level if you want to run more detailed tests from tempest. Test level 2 runs scenario tests, level 3 
runs all tempest tests that don't require an admin account.

Level 1: extension tests
------------------------
Some services return a list of installed extensions, for example Nova, Cinder and Neutron. Since every OpenStack Release adds new
extensions an educated guess can be made to report the installed OpenStack relese.
To make this also possible for other services an additional set of tempest tests is run, for example to get available Swift middlewares.

Level 2: scenario tests
-----------------------
These are longer-running tests simulating actual real-life scenarios. For example the scenario ``tempest.scenario.test_minimum_basic``
simulates this scenario: create a Glance image, boot a Nova instance, create a Cinder volume, attach it, reboot instance, add a floating
IP, ssh into server. 
Level 2 tests can be used to confirm a working OpenStack installation from an user point of view.

Level 3: detailed tests
-----------------------
These are all tests from tempest, that don't require an admin account to finish successfully. 

Testing
-------

    nosetests --with-coverage --cover-package=tempest_report
