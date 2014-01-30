
================================
Satori - Configuration Discovery
================================

[intended for OpenStack and to be proposed as an OpenStack project]

The charter for the project is focus narrowly on discovering pre-existing
infrastructure and installed or running software. For example, given a URL and
some credentials, discover which server(s) the URL is hosted on and what
software is running on those servers.


We expect that the output of such a tool - configuration information - could be
used for:

* Configuration analysis (ex. compared against a library of best practices)
* Configuration monitoring (ex. has the configuration changed?)
* Troubleshooting
* Heat Template generation
* Solum Application creation/import
* Creation of Chef recipes/cookbooks, Puppet modules, Ansible playbooks, setup
  scripts, etc..



Getting Started
===============

Run::

   pip install satori
   satori example.com

.. note::
    for full experience, use a name or IP address that is hosted on an
    OpenStack cloud with your `OS_xxx` environment variables set with
    credentials for that cloud.


Start Hacking
=============

We recommend using a virtualenv to install the client. This description
uses the `install virtualenv`_ script to create the virtualenv::

   python tools/install_venv.py
   source .venv/bin/activate
   python setup.py develop

Unit tests can be ran simply by running::

   run_tests.sh


Example uses::

    $ satori foo.com
    IP Address: 192.168.10.12

    # with nova environment variables
    $ satori www.foo.com
    Address:
       www.foo.com resolves to IPv4 address 4.4.4.4
    Host:
       4.4.4.4 (www.foo.com) is hosted on a Nova Instance
       Instance Information:
           URI: https://nova.api.somecloud.com/v2/111222/servers/d9119040-f767-
                4141-95a4-d4dbf452363a
           Name: sampleserver01.foo.com
           ID: d9119040-f767-4141-95a4-d4dbf452363a
       ip-addresses:
           public:
               ::ffff:404:404
               4.4.4.4
           private:
               10.1.1.156

Links
=====
- `OpenStack  Wiki`_
- `Launchpad Project`_

.. _OpenStack Wiki: https://wiki.openstack.org/Satori
.. _Launchpad Project: https://launchpad.net/satori
