#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#
"""Discovery Module


    TODO(zns): testing, refactoring, etc...  just using this to demonstrate
    functionality

Example usage:

    from satori import discovery
    discovery.run(address="foo.com")


"""

from __future__ import print_function

import importlib

from novaclient.v1_1 import client
import six

from satori import dns


def run(address, config):
    """Run discovery and return results."""
    results = {}
    ipaddress = dns.resolve_hostname(address)
    results['domain'] = dns.domain_info(address)
    results['address'] = ipaddress

    if config.username is not None:
        server = find_nova_host(ipaddress, config)
        if server:
            host = {'type': 'Nova instance'}

            host['uri'] = [l['href'] for l in server.links
                           if l['rel'] == 'self'][0]
            host['name'] = server.name
            host['id'] = server.id

            host['addresses'] = server.addresses

            if all([config.system_info, config.host_key]):
                module_name = config.system_info
                if '.' not in module_name:
                    module_name = 'satori.sysinfo.%s' % module_name
                system_info_module = importlib.import_module(module_name)
                result = system_info_module.get_systeminfo(host, config)
                host['system_info'] = result

            results['host'] = host

    return results


def find_nova_host(address, config):
    """See if a nova instance has the supplied address."""
    nova = client.Client(config.username,
                         config.password,
                         config.tenant_id,
                         config.authurl,
                         region_name=config.region,
                         service_type="compute")
    for server in nova.servers.list():
        for network_addresses in six.itervalues(server.addresses):
            for ipaddress in network_addresses:
                if ipaddress['addr'] == address:
                    return server
