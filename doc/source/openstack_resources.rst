=================================
OpenStack Control Plane Discovery
=================================

Satori supports :ref:`control plane <terminology_control_plane>` discovery of
resources that belong to an OpenStack tenant. A user that provides valid
OpenStack credentials will have additional information available when a
discovered resource is found to belong on that tenant (TODO: This sentence
sucks...)


OpenStack Credentials
=====================

OpenStack credentials can be provided on the command line or injected into the
shell environment variables. Satori reuses the `OpenStack Nova conventions`_ for
environment variables since many Satori users also use the `nova`_ program.

Use the export command to store the credentials in the shell environment:

::
    $ export OS_USERNAME=yourname
    $ export OS_PASSWORD=yadayadayada
    $ export OS_TENANT_NAME=myproject
    $ export OS_AUTH_URL=http://...
    $ satori foo.com

Alternatively, the credentials can be passed on the command line:

::
    $ satori foo.com \
    --os-username yourname \
    --os-password yadayadayada \
    --os-tenant-name myproject \
    --os-auth-url http://... 


Discovered Host
===============

If a discovery for a domain name or IP address is found to belong to the
tenant, the resource data will be returned. In this example, the OpenStack
credentials were provided via environment variables. The "Host" section is
only available because the control plane discovery was possible using the
OpenStack credentials.

::

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

.. _nova: https://github.com/openstack/python-novaclient
.. _OpenStack Nova conventions: https://github.com/openstack/python-novaclient/blob/master/README.rst#id1
