=============
Schema
=============

The following list of fields describes the data returned from Satori.


Target
========

Target contains the address suplplied to run the discovery.


Found
========

All data items discovered are returned under the found key. Keys to resources
discovered are also added under found, but the actual resources are stored
under the resources key.


Resources
========

All resources (servers, load balancers, DNS domains, etc...) are stored under
the resources key.
