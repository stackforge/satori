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
import urlparse

import pythonwhois
import tldextract

from satori import errors

LOG = logging.getLogger(__name__)


def resolve_hostname(host):
    """Get IP address of hostname or URL."""
    try:
        parsed = urlparse.urlparse(host)
    except AttributeError as err:
        error = "Hostname `%s`is unparseable. Error: %s" % (host, err)
        LOG.exception(error)
        raise errors.SatoriInvalidNetloc(error)

    # Domain names are in netloc, IP addresses fall into path
    hostname = parsed.netloc or parsed.path

    # socket.gaierror is not trapped here
    address = socket.gethostbyname(hostname)
    return address


def get_registered_domain(hostname):
    """Get the root DNS domain of an FQDN."""
    return tldextract.extract(hostname).registered_domain


def domain_info(domain):
    """Get as much information as possible for a given domain name."""
    domain = get_registered_domain(domain)
    result = pythonwhois.get_whois(domain)
    expires = result['expiration_date'][0]
    days_until_expires = (expires - datetime.datetime.now()).days
    return {
        'name': domain,
        'whois': result['raw'],
        'registrar': result['registrar'][0],
        'nameservers': result['nameservers'],
        'days_until_expires': days_until_expires,
    }
