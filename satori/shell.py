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

import sys

from satori import discovery


def main(argv=sys.argv[1:]):
    """Demonstrating usage."""
    if (not isinstance(argv, list)) or len(argv) < 1:
        print("No address supplied. Usage: satori [address | name | url]")
        return -1

    if '-h' in argv or '--help' in argv:
        print("Usage: satori [address | name | url]")
        return 0

    results = discovery.run(argv[0])
    output_results(argv[0], results)
    return 0


def output_results(discovered_target, results):
    """Print results in CLI format."""
    address = results['address']
    print(u"Address:\n\t%s resolves to IPv4 address %s" % (
          discovered_target, address))
    if 'host' in results:
        host = results['host']
        print(u"Host:\n\t%s (%s) is hosted on a %s" % (
              address, discovered_target, host['type']))

        print(u"\tInstance Information:")
        print(u"\t\tURI: %s" % host['uri'])
        print(u"\t\tName: %s" % host['name'])
        print(u"\t\tID: %s" % host['id'])

        print(u"\tip-addresses:")
        addresses = host.get('addresses') or {}
        for name, address_list in addresses.iteritems():
            print(u"\t\t%s:" % name)
            for server_address in address_list:
                print(u"\t\t\t%s:" % server_address['addr'])
    else:
        print(u"Host not found")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
