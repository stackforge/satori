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


def parse_target_hostname(target):
    """Get IP address or FQDN of a target which could be a URL or address."""
    if not target:
        raise errors.SatoriInvalidNetloc("Target must be supplied.")
    try:
        parsed = urlparse.urlparse(target)
    except AttributeError as err:
        error = "Target `%s` is unparseable. Error: %s" % (target, err)
        LOG.exception(error)
        raise errors.SatoriInvalidNetloc(error)

    # Domain names and IP are in netloc when parsed with a protocol
    # they will be in path if parsed without a protocol
    return parsed.netloc or parsed.path


def resolve_hostname(hostname):
    """Get IP address of hostname."""
    try:
        address = socket.gethostbyname(hostname)
    except socket.gaierror:
        error = "`%s` is an invalid domain." % hostname
        raise errors.SatoriInvalidDomain(error)
    return address


def get_registered_domain(hostname):
    """Get the root DNS domain of an FQDN."""
    return tldextract.extract(hostname).registered_domain


def ip_info(ip_address):
    """Get as much information as possible for a given ip address."""
    if not utils.is_valid_ip_address(ip_address):
        error = "`%s` is an invalid IP address." % ip_address
        raise errors.SatoriInvalidIP(error)

    result = pythonwhois.get_whois(ip_address)

    return {
        'whois': result['raw']
    }


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


def netloc_info(netloc):
    """Determine if netloc is an IP or domain name."""
    if utils.is_valid_ip_address(netloc):
        ip_info(netloc)
    else:
        domain_info(netloc)
