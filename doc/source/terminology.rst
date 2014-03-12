=============
Terminology
=============

Opinions
===================

Opinions are being discussed at https://wiki.openstack.org/wiki/Satori/OpinionsProposal.

Control Plane Discovery
=======================

Using native bindings, client libraries (pyrax, boto, novaclient, libcloud, etc.) or cloud APIs to attain information about a configuration. This requires credentials/api tokens, and could provide: a server's image data, a server's region, a load-balancer's VIPs and nodes, networking info, etc.

Data Plane Discovery
====================

Making direct observations about a configuration by running commands/utilities directly on the system, or accessing and analyzing a system's network interface. This might require login credentials for the host resource, and could provide information ranging from disk usage to packages installed to motherboard fan speeds.

SysInfo Provider
================

One of any open source applications or utilities that will examine a host machine and return verbose information about that system. Satori will leverage/support these tools for Data Plane Discovery.
