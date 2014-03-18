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

"""Discovery Module.

    TODO(zns): testing, refactoring, etc...  just using this to demonstrate
    functionality

Example usage:

    from satori import discovery
    discovery.run(address="foo.com")
"""

from __future__ import print_function

import ipaddress as ipaddress_module
from novaclient.v1_1 import client
from pythonwhois import shared
import six

from satori import dns
from satori import utils


def run(address, config, interactive=False):
    """Run discovery and return results."""
    results = {}
    if utils.is_valid_ip_address(address):
        ipaddress = address
    else:
        ipaddress = dns.resolve_hostname(address)
        #TODO(sam): Use ipaddress.ip_address.is_global
        #                   "               .is_private
        #                   "               .is_unspecified
        #                   "               .is_multicast
        #       To determine address "type"
        if not ipaddress_module.ip_address(unicode(ipaddress)).is_loopback:
            try:
                results['domain'] = dns.domain_info(address)
            except shared.WhoisException as exc:
                results['domain'] = str(exc)

    results['address'] = ipaddress

    results['host'] = host = {'type': 'Undetermined'}
    if config.username is not None:
        server = find_nova_host(ipaddress, config)
        if server:
            host['type'] = 'Nova instance'
            host['uri'] = [l['href'] for l in server.links
                           if l['rel'] == 'self'][0]
            host['name'] = server.name
            host['id'] = server.id
            host['addresses'] = server.addresses
    if config.system_info:
        module_name = config.system_info.replace("-", "_")
        if '.' not in module_name:
            module_name = 'satori.sysinfo.%s' % module_name
        system_info_module = utils.import_object(module_name)
        result = system_info_module.get_systeminfo(ipaddress, config,
                                                   interactive=interactive)
        host['system_info'] = result
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
