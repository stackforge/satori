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

"""Command-line interface to Configuration Discovery.

Accept a network location, run through the discovery process and report the
findings back to the user.

"""

from __future__ import print_function

import argparse
import sys

from satori import discovery


def main():
    """Discover an existing configuration for a network location."""
    parser = argparse.ArgumentParser(description='Configuration discovery.')
    parser.add_argument(
        'netloc',
        help='Network location. E.g. https://domain.com, sub.domain.com, or '
             '4.3.2.1'
    )

    args = parser.parse_args()
    results = discovery.run(args.netloc)
    output_results(args.netloc, results)
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
    sys.exit(main())
