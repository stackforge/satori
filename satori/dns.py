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
"""Satori DNS Discovery."""

import datetime
import logging
import socket

import pythonwhois
from six.moves.urllib import parse as urlparse
import tldextract

from satori import errors
from satori import utils


LOG = logging.getLogger(__name__)


def resolve_hostname(host):
    """Get IP address of hostname or URL."""
    try:
        if not host:
            raise AttributeError("Host must be supplied.")
        parsed = urlparse.urlparse(host)
    except AttributeError as err:
        error = "Hostname `%s` is unparseable. Error: %s" % (host, err)
        LOG.exception(error)
        raise errors.SatoriInvalidNetloc(error)

    # Domain names and IP are in netloc when parsed with a protocol
    # they will be in path if parsed without a protocol
    hostname = parsed.netloc or parsed.path

    try:
        address = socket.gethostbyname(hostname)
    except socket.gaierror:
        error = "`%s` is an invalid domain." % hostname
        raise errors.SatoriInvalidDomain(error)
    return address


def get_registered_domain(hostname):
    """Get the root DNS domain of an FQDN."""
    return tldextract.extract(hostname).registered_domain


def domain_info(domain):
    """Get as much information as possible for a given domain name."""
    registered_domain = get_registered_domain(domain)
    if utils.is_valid_ip_address(domain) or registered_domain == '':
        error = "`%s` is an invalid domain." % domain
        raise errors.SatoriInvalidDomain(error)

    result = pythonwhois.get_whois(registered_domain)
    registrar = []
    if 'registrar' in result and len(result['registrar']) > 0:
        registrar = result['registrar'][0]
    nameservers = result.get('nameservers', [])
    days_until_expires = None
    expires = None
    if 'expiration_date' in result:
        if (isinstance(result['expiration_date'], list)
                and len(result['expiration_date']) > 0):
            expires = result['expiration_date'][0]
            if isinstance(expires, datetime.datetime):
                days_until_expires = (expires - datetime.datetime.now()).days
                expires = utils.get_time_string(time_obj=expires)
            else:
                days_until_expires = (utils.parse_time_string(expires) -
                                      datetime.datetime.now()).days
    return {
        'name': registered_domain,
        'whois': result['raw'],
        'registrar': registrar,
        'nameservers': nameservers,
        'days_until_expires': days_until_expires,
        'expiration_date': expires,
    }
