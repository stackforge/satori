=================================
OpenStack Configuration Discovery
=================================

Satori is a configuration discovery tool for OpenStack and OpenStack tenant hosted applications.

.. toctree::
   :maxdepth: 1

   contributing
   releases
   terminology


Get Satori
------------

To install satori, simply run pip install.

::

   $ pip install satori

Use Satori
-----------

::

   $ satori discover www.foo.com
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

Please go read more in the README in the `Code`_.
Also check the `OpenStack Wiki`_'s Getting started section.


Links
=====
- `OpenStack Wiki`_
- `Code`_
- `Launchpad Project`_
- `Features`_
- `Issues`_

.. _OpenStack Wiki: https://wiki.openstack.org/Satori
.. _OpenStack tenant environment variables: http://docs.openstack.org/developer/python-novaclient/shell.html
.. _related OpenStack project: https://wiki.openstack.org/wiki/ProjectTypes
.. _install virtualenv: https://github.com/stackforge/satori/blob/master/tools/install_venv.py
.. _Code: https://github.com/stackforge/satori
.. _Launchpad Project: https://launchpad.net/satori
.. _Features: https://blueprints.launchpad.net/satori
.. _Issues: https://bugs.launchpad.net/satori/

Index
-----

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
