===============
Getting Started
===============

Satori is currently a simple command-line tool so that new users can discover a configuration without needing to setup additional infrastructure:

::

    $ satori --os-username <username> --os-password <password> --os-tenant-id <tenant-id> --os-auth-url <auth-endpoint> --os-region-name <region> www.example.com
    Address:
            www.example.com resolves to IPv4 address 10.1.0.44
    Domain: www.example.com
            Registrar: TUCOWS, INC.
            Nameservers: DNS1.EXAMPLE.COM, DNS2.EXAMPLE.COM
            Expires: 256 days
    Host:
            10.1.0.44 (www.example.com) is hosted on a Nova instance
            Instance Information:
                    URI: https://<region>.servers.api.example.com/v2/123456/servers/fb52d194-1f60-4d23-b35f-d13e7bef9381
                    Name: www.example.com
                    ID: fb52d194-1f60-4d23-b35f-d13e7bef9381
            ip-addresses:
                    public:
                            2001:0db8:85a3:0042:1000:8a2e:0370:7334:
                            10.1.0.44:
                    private:
                            10.2.99.140:
