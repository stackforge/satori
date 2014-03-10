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
import logging
import os
import sys

import six

from satori.common import logging as common_logging
from satori import discovery

LOG = logging.getLogger(__name__)


def main():
    """Discover an existing configuration for a network location."""
    parser = argparse.ArgumentParser(description='Configuration discovery.')
    parser.add_argument(
        'netloc',
        help='Network location. E.g. https://domain.com, sub.domain.com, or '
             '4.3.2.1'
    )
    openstack_group = parser.add_argument_group(
        'OpenStack Settings',
        'Cloud credentials, settings and endpoints. If a network location is '
        'found to be hosted on the tenant additional information is provided.'
    )

    openstack_group.add_argument(
        '--os-username',
        dest='username',
        default=os.environ.get('OS_USERNAME'),
        help='OpenStack Auth username. Defaults to env[OS_USERNAME].'
    )
    openstack_group.add_argument(
        '--os-password',
        dest='password',
        default=os.environ.get('OS_PASSWORD'),
        help='OpenStack Auth password. Defaults to env[OS_PASSWORD].'
    )
    openstack_group.add_argument(
        '--os-region-name',
        dest='region',
        default=os.environ.get('OS_REGION_NAME'),
        help='OpenStack region. Defaults to env[OS_REGION_NAME].'
    )
    openstack_group.add_argument(
        '--os-auth-url',
        dest='authurl',
        default=os.environ.get('OS_AUTH_URL'),
        help='OpenStack Auth endpoint. Defaults to env[OS_AUTH_URL].'
    )
    openstack_group.add_argument(
        '--os-compute-api-version',
        dest='compute_api_version',
        default=os.environ.get('OS_COMPUTE_API_VERSION', '1.1'),
        help='OpenStack Compute API version. Defaults to '
             'env[OS_COMPUTE_API_VERSION] or 1.1.'
    )

    # Tenant name or ID can be supplied
    tenant_group = openstack_group.add_mutually_exclusive_group()
    tenant_group.add_argument(
        '--os-tenant-name',
        dest='tenant_name',
        default=os.environ.get('OS_TENANT_NAME'),
        help='OpenStack Auth tenant name. Defaults to env[OS_TENANT_NAME].'
    )
    tenant_group.add_argument(
        '--os-tenant-id',
        dest='tenant_id',
        default=os.environ.get('OS_TENANT_ID'),
        help='OpenStack Auth tenant ID. Defaults to env[OS_TENANT_ID].'
    )

    parser.add_argument(
        '--host-key-path',
        type=argparse.FileType('r'),
        help='SSH key to access Nova resources.'
    )

    parser.add_argument(
        '--system-info',
        help='Mechanism to use on a Nova resource to obtain system '
             'information. E.g. ohai, facts, factor.'
    )

    # Output formatting
    parser.add_argument(
        "--logconfig",
        help="Optional logging configuration file"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="turn on additional debugging inspection and "
        "output including full HTTP requests and responses. "
        "Log output includes source file path and line "
        "numbers."
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="turn up logging to DEBUG (default is INFO)"
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="turn down logging to WARN (default is INFO)"
    )

    args = parser.parse_args()

    common_logging.init_logging(args)

    if args.host_key_path:
        args.host_key = args.host_key_path.read()

    # argparse lacks a method to say "if this option is set, require these too"
    required_to_access_cloud = [
        args.username,
        args.password,
        args.authurl,
        args.region,
        args.tenant_name or args.tenant_id,
    ]
    if args.username and not all(required_to_access_cloud):
        parser.error("To connect to an OpenStack cloud you must supply a "
                     "username, password, authentication enpoind, region and "
                     "tenant. Either provide all of these settings or none of "
                     "them.")

    try:
        results = discovery.run(args.netloc, args)
        output_results(args.netloc, results)
    except Exception as exc:  # pylint: disable=W0703
        if args.debug:
            LOG.exception(exc)
        return str(exc)
    return 0


def output_results(discovered_target, results):
    """Print results in CLI format."""
    address = results['address']
    print(u"Address:\n\t%s resolves to IPv4 address %s" % (
          discovered_target, address))

    if 'domain' in results:
        print(u"Domain: %s" % results['domain']['name'])
        print(u"\tRegistrar: %s" % results['domain']['registrar'])
        if results['domain']['nameservers']:
            print(u"\tNameservers: %s" % (
                  ", ".join(results['domain']['nameservers'])
                  ))
        if results['domain'].get('days_until_expires') is not None:
            print(u"\tExpires: %d days" %
                  results['domain']['days_until_expires'])

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
        for name, address_list in six.iteritems(addresses):
            print(u"\t\t%s:" % name)
            for server_address in address_list:
                print(u"\t\t\t%s:" % server_address['addr'])

        if 'system_info' in host:
            print(u"\tSystem Information:")
            print(u"\t\t%s" % host['system_info'])

    else:
        print(u"Host not found")


if __name__ == "__main__":
    sys.exit(main())
