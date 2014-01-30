#   Copyright 2012-2013 OpenStack Foundation
#
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

"""Command-line interface to Configuration Discovery


    TODO(zns): testing, refactoring, etc...  just using this to demonstrate
    functionality


"""

from __future__ import print_function

import os
import socket
import sys
import urlparse

from novaclient.v1_1 import client


def resolve_hostname(host):
    """Get IP address of hostname or URL.
    """
    parsed = urlparse.urlparse(host)
    hostname = parsed.netloc or parsed.path
    address = socket.gethostbyname(hostname)
    return address


def find_nova_host(address):
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


def main(argv=sys.argv[1:]):
    """Demonstrating usage."""
    address = resolve_hostname(argv[0])
    print(u"Address:\n\t%s resolves to IPv4 address %s" % (
          argv[0], address))
    server = find_nova_host(address) if 'OS_USERNAME' in os.environ else None
    if server:
        print(u"Host:\n\t%s (%s) is hosted on a Nova instance" % (address,
                                                                  argv[0]))

        print(u"\tInstance Information:")
        print(u"\t\tURI: %s" % [l['href'] for l in server.links
                                if l['rel'] == 'self'][0])
        print(u"\t\tName: %s" % server.name)
        print(u"\t\tID: %s" % server.id)

        print(u"\tip-addresses:")
        for name, addresses in server.addresses.iteritems():
            print(u"\t\t%s:" % name)
            for server_address in addresses:
                print(u"\t\t\t%s:" % server_address['addr'])

    else:
        print(u"Host not found")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
