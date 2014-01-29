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

import socket
import sys
import urlparse


def resolve_hostname(host):
    """Get IP address of hostname or URL.
    """
    parsed = urlparse.urlparse(host)
    hostname = parsed.netloc or parsed.path
    address = socket.gethostbyname(hostname)
    return address


def main(argv=sys.argv[1:]):
    """Demonstrating usage."""
    print(u"IP Address: %s" % resolve_hostname(argv[0]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
