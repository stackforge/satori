=================================
OpenStack Configuration Discovery
=================================

Satori is a configuration discovery tool for OpenStack and OpenStack tenant hosted applications.

.. toctree::
   :maxdepth: 1

   contributing
   releases


Get Satori
------------

To install satori, simply run pip install.

::

  $ pip install satori

Use Satori
-----------

Satori will 'dig' and 'whois' and check DNS records as well as then discover more config if you own the unerlying openstack infrastructure if you have the credentials loaded correctly. In this specific example below we do not.

::

  $ satori openstack.org
	Address:
		openstack.org resolves to IPv4 address 174.143.194.225
	Domain: openstack.org
		Registrar: CSC Corporate Domains, Inc. (R24-LROR)
		Nameservers: DNS2.STABLETRANSIT.COM, DNS1.STABLETRANSIT.COM
		Expires: 214 days
	Host not found


You will find more detailed example in the README in the `Code`_.
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
