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

"""Satori main module."""

__all__ = ('__version__')

try:
    import eventlet
    eventlet.monkey_patch()
except ImportError:
    pass

import pbr.version

from satori import shell


version_info = pbr.version.VersionInfo('satori')
try:
    __version__ = version_info.version_string()
except AttributeError:
    __version__ = None


def discover(address=None):
    """Temporary to demo python API.

    TODO(zns): make it real
    """
    shell.main(argv=[address])
    return {'address': address, 'other info': '...'}
