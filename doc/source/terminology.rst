=============
Terminology
=============

Opinions
========

Opinions are being discussed at https://wiki.openstack.org/wiki/Satori/OpinionsProposal.

Control Plane Discovery
=======================

Control plane discovery is the process of making API calls to management
systems like OpenStack or IT asset management systems. An external management
system can show relationships between resources that can further improve
the discovery process. For example, a data plane discovery of a single server
will reveal that a server has a storage device attached to it. Control plane
discovery using an OpenStack plugin can reveal the details of the Cinder
volume.

Satori can load plugins that enable these systems to be queried.

Data Plane Discovery
====================

Data plane discovery is the process of connecting to a resource and using
native tools to extract information. For example, it can provide information
about the user list, installed software and processes that are running.

Satori can load plugins that enable data plane discovery.
