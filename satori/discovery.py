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

import os
import socket
import urlparse

from novaclient.v1_1 import client


def run(address):
    """Run discovery and return results."""
    results = {}
    ipaddress = resolve_hostname(address)
    results['address'] = ipaddress

    server = find_nova_host(ipaddress) if 'OS_USERNAME' in os.environ else None
    if server:
        host = {'type': 'Nova instance'}

        host['uri'] = [l['href'] for l in server.links
                       if l['rel'] == 'self'][0]
        host['name'] = server.name
        host['id'] = server.id

        host['addresses'] = server.addresses
        results['host'] = host
    return results


def resolve_hostname(host):
    """Get IP address of hostname or URL."""
    parsed = urlparse.urlparse(host)
    hostname = parsed.netloc or parsed.path
    address = socket.gethostbyname(hostname)
    return address


def find_nova_host(address):
    """See if a nova instance has the supplied address."""
    nova = client.Client(os.environ['OS_USERNAME'],
                         os.environ['OS_PASSWORD'],
                         os.environ['OS_TENANT_ID'],
                         os.environ['OS_AUTH_URL'],
                         region_name=os.environ['OS_REGION_NAME'],
                         service_type="compute")
    for server in nova.servers.list():
        for network_addresses in server.addresses.itervalues():
            for ipaddress in network_addresses:
                if ipaddress['addr'] == address:
                    return server
