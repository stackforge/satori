
================================
Satori - Configuration Discovery
================================

Satori provides configuration discovery for existing infrastructure. It is
a `related OpenStack project`_.

The charter for the project is to focus narrowly on discovering pre-existing
infrastructure and installed or running software. For example, given a URL and
some credentials, discover which resources (load balancer and servers) the URL
is hosted on and what software is running on those servers.

Configuration discovery output could be used for:

* Configuration analysis (ex. compared against a library of best practices)
* Configuration monitoring (ex. has the configuration changed?)
* Troubleshooting
* Heat Template generation
* Solum Application creation/import
* Creation of Chef recipes/cookbooks, Puppet modules, Ansible playbooks, setup
  scripts, etc..

Getting Started
===============

Run WITHOUT OpenStack credentials::

   $ pip install satori

   $ satori www.foo.com
    Address:
        www.foo.com resolves to IPv4 address 4.4.4.4
    Domain: foo.com
        Registrar: TUCOWS, INC.
    Nameservers: NS1.DIGIMEDIA.COM, NS2.DIGIMEDIA.COM
        Expires: 457 days
    Host not found

Deeper discovery is available if the network location (IP or hostname) is
hosted on an OpenStack cloud tenant that Satori can access.

Cloud settings can be passed in on the command line or via `OpenStack tenant environment
variables`_.


Run LOCALLY

   $ pip install satori

   $ satori localhost --system-info=ohai-solo
   # Installs and runs ohai-solo


Run WITH OpenStack credentials::

   $ satori foo.com --os-username yourname --os-password yadayadayada --os-tenant-name myproject --os-auth-url http://...

Or::

   $ export OS_USERNAME=yourname
   $ export OS_PASSWORD=yadayadayada
   $ export OS_TENANT_NAME=myproject
   $ export OS_AUTH_URL=http://...
   $ satori foo.com

Notice the discovery result now contains a ``Host`` section::

   $ satori www.foo.com
   Domain: foo.com
     Registered at TUCOWS DOMAINS INC.
     Expires in 475 days.
     Name servers:
         DNS1.STABLETRANSIT.COM
         DNS2.STABLETRANSIT.COM
   Address:
     www.foo.com resolves to IPv4 address 4.4.4.4
   Host:
     4.4.4.4 (www.foo.com) is hosted on a Nova Instance
     Instance Information:
         URI: https://nova.api.somecloud.com/v2/111222/servers/d9119040-f767-414
              1-95a4-d4dbf452363a
         Name: sampleserver01.foo.com
         ID: d9119040-f767-4141-95a4-d4dbf452363a
     ip-addresses:
         public:
             ::ffff:404:404
             4.4.4.4
         private:
             10.1.1.156
     System Information:
         Ubuntu 12.04 installed
         Server was rebooted 11 days, 22 hours ago
         /dev/xvda1 is using 9% of its inodes.
     Running Services:
         httpd on 127.0.0.1:8080
         varnishd on 0.0.0.0:80
         sshd on 0.0.0.0:22
     httpd:
         Using 7 of 100 MaxClients

Documentation
=============

Additional documentation is located in the ``doc/`` directory and is hosted at
http://satori.readthedocs.org/.

Start Hacking
=============

We recommend using a virtualenv to install the client. This description
uses the `install virtualenv`_ script to create the virtualenv::

   $ python tools/install_venv.py
   $ source .venv/bin/activate
   $ python setup.py develop

Unit tests can be ran simply by running::

   $ tox

   # or, just style checks
   $ tox -e pep8

   # or, just python 2.7 checks
   $ tox -e py27


Running a test coverage report:

   # cleanup previous runs
   $ rm -rf cover && rm -rf covhtml && rm .coverage

   # Run tests and generate the report
   $ tox -ecover && coverage html -d covhtml -i

   # open it in a broweser
   $ open covhtml/index.html

Checking test coverage::

  $ tox -ecover
  $ coverage html -d covhtml -i
  $ open covhtml/index.html  # opens the report in a browser


Links
=====
- `OpenStack  Wiki`_
- `Documentation`_
- `Code`_
- `Launchpad Project`_
- `Features`_
- `Issues`_

.. _OpenStack Wiki: https://wiki.openstack.org/Satori
.. _Documentation: http://satori.readthedocs.org/
.. _OpenStack tenant environment variables: http://docs.openstack.org/developer/python-novaclient/shell.html
.. _related OpenStack project: https://wiki.openstack.org/wiki/ProjectTypes
.. _install virtualenv: https://github.com/stackforge/satori/blob/master/tools/install_venv.py
.. _Code: https://github.com/stackforge/satori
.. _Launchpad Project: https://launchpad.net/satori
.. _Features: https://blueprints.launchpad.net/satori
.. _Issues: https://bugs.launchpad.net/satori/
