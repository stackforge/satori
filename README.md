Satori - Configuration Discovery
===============================

[intended for OpenStack and to be proposed as an OpenStack project]

The charter for the project is focus narrowly on discovering pre-existing infrastructure and installed or running software. For example, given a URL and some credentials, discover which server(s) the URL is hosted on and what software is running on those servers.


We expect that the output of such a tool - configuration information - could be used for:
- Configuration analysis (ex. compared against a library of best practices)
- Configuration monitoring (ex. has the configuration changed?)
- Troubleshooting
- Heat Template generation
- Solum Application creation/import
- Creation of Chef recipes/cookbooks, Puppet modules, Ansible playbooks, setup scripts, etc..



## Links
- [wiki](https://wiki.openstack.org/Satori)
- [Launchpad project](https://launchpad.net/satori)
