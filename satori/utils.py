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
"""General utilities.

- Class and module import/export
- Time utilities (we standardize on UTC)
"""

import datetime
import inspect
import logging
import platform
import socket
import sys
import time

import iso8601

LOG = logging.getLogger(__name__)
STRING_FORMAT = "%Y-%m-%d %H:%M:%S +0000"


def import_class(import_str):
    """Return a class from a string including module and class."""
    mod_str, _, class_str = import_str.rpartition('.')
    try:
        __import__(mod_str)
        return getattr(sys.modules[mod_str], class_str)
    except (ImportError, ValueError, AttributeError) as exc:
        LOG.debug('Inner Exception: %s', exc)
        raise


def import_object(import_str, *args, **kw):
    """Return an object including a module or module and class."""
    try:
        __import__(import_str)
        return sys.modules[import_str]
    except ImportError:
        cls = import_class(import_str)
        return cls(*args, **kw)


def get_time_string(time_obj=None):
    """The canonical time string format (in UTC).

    :param time_obj: an optional datetime.datetime or timestruct (defaults to
                     gm_time)

    Note: Changing this function will change all times that this project uses
    in the returned data.
    """
    if isinstance(time_obj, datetime.datetime):
        if time_obj.tzinfo:
            offset = time_obj.tzinfo.utcoffset(time_obj)
            utc_dt = time_obj + offset
            return datetime.datetime.strftime(utc_dt, STRING_FORMAT)
        return datetime.datetime.strftime(time_obj, STRING_FORMAT)
    elif isinstance(time_obj, time.struct_time):
        return time.strftime(STRING_FORMAT, time_obj)
    elif time_obj is not None:
        raise TypeError("get_time_string takes only a time_struct, none, or a "
                        "datetime. It was given a %s" % type(time_obj))
    return time.strftime(STRING_FORMAT, time.gmtime())


def parse_time_string(time_string):
    """Return naive datetime object from string in standard time format."""
    parsed = time_string.replace(" +", "+").replace(" -", "-")
    dt_with_tz = iso8601.parse_date(parsed)
    offset = dt_with_tz.tzinfo.utcoffset(dt_with_tz)
    result = dt_with_tz + offset
    return result.replace(tzinfo=None)


def is_valid_ipv4_address(address):
    """Check if the address supplied is a valid IPv4 address."""
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:  # not a valid address
        return False
    return True


def is_valid_ipv6_address(address):
    """Check if the address supplied is a valid IPv6 address."""
    try:
        socket.inet_pton(socket.AF_INET6, address)
    except socket.error:  # not a valid address
        return False
    return True


def is_valid_ip_address(address):
    """Check if the address supplied is a valid IP address."""
    return is_valid_ipv4_address(address) or is_valid_ipv6_address(address)


def get_local_ips():
    """Return local ipaddress(es)."""
    # pylint: disable=W0703
    list1 = []
    list2 = []
    defaults = ["127.0.0.1", r"fe80::1%lo0"]

    hostname = None
    try:
        hostname = socket.gethostname()
    except Exception as exc:
        LOG.debug("Error in gethostbyname_ex: %s", exc)

    try:
        _, _, addresses = socket.gethostbyname_ex(hostname)
        list1 = [ip for ip in addresses]
    except Exception as exc:
        LOG.debug("Error in gethostbyname_ex: %s", exc)

    try:
        list2 = [info[4][0] for info in socket.getaddrinfo(hostname, None)]
    except Exception as exc:
        LOG.debug("Error in getaddrinfo: %s", exc)

    return list(set(list1 + list2 + defaults))


def get_platform_info():
    """Return a dictionary with distro, version, and system architecture.

    Requires >= Python 2.4 (2004)

    Supports most Linux distros, Mac OSX, and Windows.

    Example return value on Mac OSX:

        {'arch': '64bit', 'version': '10.8.5', 'dist': 'darwin'}

    """
    pin = list(platform.dist() + (platform.machine(),))
    pinfodict = {'dist': pin[0], 'version': pin[1], 'arch': pin[3]}
    if not pinfodict['dist'] or not pinfodict['version']:
        pinfodict['dist'] = sys.platform.lower()
        pinfodict['arch'] = platform.architecture()[0]
        if 'darwin' in pinfodict['dist']:
            pinfodict['version'] = platform.mac_ver()[0]
        elif pinfodict['dist'].startswith('win'):
            pinfodict['version'] = str(platform.platform())

    return pinfodict


def get_source_definition(function, with_docstring=False):
    """Get the entire body of a function, including the signature line.

    :param with_docstring: Include docstring in return value.
                           Default is False. Supports docstrings in
                           triple double-quotes or triple single-quotes.
    """
    thedoc = inspect.getdoc(function)
    definition = inspect.cleandoc(
        inspect.getsource(function))
    if thedoc and not with_docstring:
        definition = definition.replace(thedoc, '')
        doublequotes = definition.find('"""')
        doublequotes = float("inf") if doublequotes == -1 else doublequotes
        singlequotes = definition.find("'''")
        singlequotes = float("inf") if singlequotes == -1 else singlequotes
        if doublequotes != singlequotes:
            triplet = '"""' if doublequotes < singlequotes else "'''"
            definition = definition.replace(triplet, '', 2)
    while definition.find('\n\n\n') != -1:
        definition = definition.replace('\n\n\n', '\n\n')

    definition_copy = []
    for line in definition.split('\n'):
        # pylint: disable=W0141
        if not any(map(line.strip().startswith, ("@", "def"))):
            line = " " * 4 + line
        definition_copy.append(line)

    return "\n".join(definition_copy).strip()


def get_source_body(function, with_docstring=False):
    """Get the body of a function (i.e. no definition line, unindented).

    :param with_docstring: Include docstring in return value.
                           Default is False.
    """
    lines = get_source_definition(
        function, with_docstring=with_docstring).split('\n')

    # Find body - skip decorators and definition
    start = 0
    for number, line in enumerate(lines):
        # pylint: disable=W0141
        if any(map(line.strip().startswith, ("@", "def"))):
            start = number + 1

    lines = lines[start:]

    # Unindent body
    indent = len(lines[0]) - len(lines[0].lstrip())
    for index, line in enumerate(lines):
        lines[index] = line[indent:]
    return '\n'.join(lines).strip()
