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

import socket

from freezegun import freeze_time
import mock
import pythonwhois

from satori import dns
from satori import errors
from satori.tests import utils


class TestDNS(utils.TestCase):

    def setUp(self):
        self.ip = "4.3.2.1"
        self.domain = "domain.com"
        self.mysocket = socket
        self.mysocket.gethostbyname = mock.MagicMock(name='gethostbyname')

        self.WHOIS = ["""
            The data in Fake Company WHOIS database is provided
            by Fake Company for information purposes only. By submitting
            WHOIS query, you agree that you will use this data only for lawful
            purpose. In addition, you agree not to:
            (a) use the data to allow, enable, or otherwise support marketing
            activities, regardless of the medium. Such media include but are
            not limited to e-mail, telephone, facsimile, postal mail, SMS, and
            wireless alerts; or
            (b) use the data to enable high volume, electronic processes
            that sendqueries or data to the systems of any Registry Operator or
            ICANN-Accredited registrar, except as necessary to register
            domain names or modify existing registrations.
            (c) sell or redistribute the data except insofar as it has been
            incorporated into a value-added product that does not permit
            the extraction of a portion of the data from the value-added
            product or service for use by other parties.
            Fake Company reserves the right to modify these terms at any time.
            Fake Company cannot guarantee the accuracy of the data provided.
            By accessing and using Fake Company WHOIS service, you agree to
            these terms.

            NOTE: FAILURE TO LOCATE A RECORD IN THE WHOIS DATABASE IS NOT
            INDICATIVE OF THE AVAILABILITY OF A DOMAIN NAME.

            Domain Name: mytestdomain.com
            Registry Domain ID:
            Registrar WHOIS Server: whois.fakecompany.com
            Registrar URL: http://www.fakecompany.com
            Updated Date: 2013-08-15T05:02:28Z
            Creation Date: 2010-11-01T23:57:06Z
            Registrar Registration Expiration Date: 2020-01-01T00:00:00Z
            Registrar: Fake Company, Inc
            Registrar IANA ID: 106
            Registrar Abuse Contact Email: abuse@fakecompany.com
            Registrar Abuse Contact Phone: +44.2070159370
            Reseller:
            Domain Status: ACTIVE
            Registry Registrant ID:
            Registrant Name: Host Master
            Registrant Organization: Rackspace US, Inc.
            Registrant Street: 5000 Walzem Road
            Registrant City: San Antonio,
            Registrant State/Province: Texas
            Registrant Postal Code: 78218
            Registrant Country: US
            Registrant Phone:
            Registrant Phone Ext:
            Registrant Fax:
            Registrant Fax Ext:
            Registrant Email:
            Registry Admin ID:
            Admin Name: Host Master
            Admin Organization: Rackspace US, Inc.
            Admin Street: 5000 Walzem Road
            Admin City:  San Antonio,
            Admin State/Province: Texas
            Admin Postal Code: 78218
            Admin Country: US
            Admin Phone: +1.2103124712
            Admin Phone Ext:
            Admin Fax:
            Admin Fax Ext:
            Admin Email: domains@rackspace.com
            Registry Tech ID:
            Tech Name: Domain Administrator
            Tech Organization: NetNames Hostmaster
            Tech Street: 3rd Floor Prospero House
            Tech Street: 241 Borough High Street
            Tech City: Borough
            Tech State/Province: London
            Tech Postal Code: SE1 1GA
            Tech Country: GB
            Tech Phone: +44.2070159370
            Tech Phone Ext:
            Tech Fax: +44.2070159375
            Tech Fax Ext:
            Tech Email: corporate-services@netnames.com
            Name Server: ns1.domain.com
            Name Server: ns2.domain.com
            DNSSEC:
            URL of the ICANN WHOIS Data Problem System: http://wdprs.fake.net/
            >>> Last update of WHOIS database: 2014-02-18T03:39:52 UTC <<<
            """]

        self.mynet = pythonwhois.net
        self.mynet.get_whois_raw = mock.MagicMock()
        self.mynet.get_whois_raw.return_value = self.WHOIS

        super(TestDNS, self).setUp()

    def test_resolve_domain_name_returns_ip(self):
        self.mysocket.gethostbyname.return_value = self.ip
        self.assertEqual(self.ip, dns.resolve_hostname(self.domain))

    def test_resolve_ip_returns_ip(self):
        self.mysocket.gethostbyname.return_value = self.ip
        self.assertEqual(self.ip, dns.resolve_hostname(self.ip))

    def test_resolve_int_raises_invalid_netloc_error(self):
        self.assertRaises(
            errors.SatoriInvalidNetloc,
            dns.resolve_hostname,
            100)

    def test_resolve_none_raises_invalid_netloc_error(self):
        self.assertRaises(
            errors.SatoriInvalidNetloc,
            dns.resolve_hostname,
            None)

    def test_registered_domain_subdomain_removed(self):
        self.assertEqual(
            self.domain,
            dns.get_registered_domain("www." + self.domain)
        )

    def test_registered_domain_path_removed(self):
        self.assertEqual(
            self.domain,
            dns.get_registered_domain("www." + self.domain + "/path")
        )

    def test_domain_info_returns_nameservers_from_whois(self):
        data = dns.domain_info(self.domain)
        self.assertEqual(
            ['ns1.domain.com', 'ns2.domain.com'],
            data['nameservers']
        )

    def test_domain_info_returns_registrar_from_whois(self):
        data = dns.domain_info(self.domain)
        self.assertEqual(
            'Fake Company, Inc',
            data['registrar']
        )

    def test_domain_info_returns_domain_name_from_parameter(self):
        data = dns.domain_info(self.domain)
        self.assertEqual(
            self.domain,
            data['name']
        )

    def test_domain_info_returns_slimmed_down_domain_name(self):
        data = dns.domain_info("s1.www." + self.domain)
        self.assertEqual(
            self.domain,
            data['name']
        )

    @freeze_time("2019-01-01")
    def test_domain_info_returns_365_day_expiration(self):
        data = dns.domain_info(self.domain)
        self.assertEqual(
            365,
            data['days_until_expires']
        )

    def test_domain_info_returns_array_of_strings_whois_data(self):
        data = dns.domain_info(self.domain)
        self.assertIsInstance(data['whois'][0], str)
