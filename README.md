# tempest-report

tempest-report is a tool for OpenStack Tempest to test remote installations and summarize found services and extensions.

Installation
------------

0) *Optional*: install some requirements from your distribution

It might be a good idea to install some libraries from your distribution repository.
Using a bare Ubuntu Server install you might want to install these packages from OS repos:

    apt-get install python-lxml python-greenlet

This avoids compilation during the next required step.

1) Install requirements

    pip install -r requirements.txt

2) Install tempest_report

    python setup.py install


Execution
---------

1) Set environment variables (you can also use the command line switches, but this will show up in your shell history):

    export OS_USERNAME=demo
    export OS_PASSWORD=devstack
    export OS_AUTH_URL=http://127.0.0.1:5000/v2.0/

2) Run basic tests:

    $ tempest_report

    Please set OS_USERNAME, OS_PASSWORD and OS_AUTH_URL. Using local devstack defaults.
    
    OK: tempest.api.object_storage.test_object_temp_url
    OK: tempest.api.object_storage.test_object_expiry
    OK: tempestwebui/tempest_extensions/test_volume_support.py
    OK: tempestwebui/tempest_extensions/test_multinic.py
    OK: tempest.api.object_storage.test_container_sync
    OK: tempest.api.object_storage.test_object_version
    OK: tempest.api.object_storage.test_container_quotas
    OK: tempest.api.object_storage.test_container_staticweb
    
    Compute (Nova): Essex
                            Volume Support
                            Multi-NIC Support
    
    Object Storage (Swift): Grizzly
                            Temporary object URL
                            Expiring Objects
                            Container sync
                            Object versioning
                            Container Quota
                            Static Web


Full output can be found in tempest-report-<timestamp>.log


Testing
-------

    nosetests --with-coverage --cover-package=tempest_report
