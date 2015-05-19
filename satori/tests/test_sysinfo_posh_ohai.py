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
"""Test PoSh-Ohai Plugin."""

import unittest
import doctest

from satori.sysinfo import posh_ohai


def load_tests(loader, tests, ignore):
    """Include doctests as unit tests."""
    tests.addTests(doctest.DocTestSuite(posh_ohai))
    return tests


if __name__ == "__main__":
    unittest.main()
