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
"""Satori Discovery Errors."""


class SatoriException(Exception):

    """Parent class for Satori exceptions.

    Accepts a string error message that that accept a str description.
    """


class UndeterminedPlatform(SatoriException):

    """The target system's platform could not be determined."""


class SatoriInvalidNetloc(SatoriException):

    """Netloc that cannot be parsed by `urlparse`."""


class SatoriInvalidDomain(SatoriException):

    """Invalid Domain provided."""


class SatoriInvalidIP(SatoriException):

    """Invalid IP provided."""


class SatoriShellException(SatoriException):

    """Invalid shell parameters."""


class GetPTYRetryFailure(SatoriException):

    """Tried to re-run command with get_pty to no avail."""


class DiscoveryException(SatoriException):

    """Discovery exception with custom message."""


class SatoriDuplicateCommandException(SatoriException):

    """The command cannot be run because it was already found to be running."""


class UnsupportedPlatform(DiscoveryException):

    """Unsupported operating system or distro."""


class SystemInfoCommandMissing(DiscoveryException):

    """Command that provides system information is missing."""


class SystemInfoCommandOld(DiscoveryException):

    """Command that provides system information is outdated."""


class SystemInfoNotJson(DiscoveryException):

    """Command did not produce valid JSON."""


class SystemInfoMissingJson(DiscoveryException):

    """Command did not produce stdout containing JSON."""


class SystemInfoCommandInstallFailed(DiscoveryException):

    """Failed to install package that provides system information."""
