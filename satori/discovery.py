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

import socket

from novaclient.v1_1 import client
import six

from satori import dns
from satori import utils


def is_valid_ipv4_address(address):
    """Check if the address supplied is a valid IPv4 address."""
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:  # not a valid address
        return False
    return True


def is_valid_ipv6_address(address):
    """Check if the address supplied is a valid IPv6 address."""
    try:
        socket.inet_pton(socket.AF_INET6, address)
    except socket.error:  # not a valid address
        return False
    return True


def is_valid_ip_address(address):
    """Check if the address supplied is a valid IP address."""
    return is_valid_ipv4_address(address) or is_valid_ipv6_address(address)


def run(address, config, interactive=False):
    """Run discovery and return results."""
    results = {}
    if is_valid_ip_address(address):
        ipaddress = address
    else:
        ipaddress = dns.resolve_hostname(address)
        results['domain'] = dns.domain_info(address)
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
