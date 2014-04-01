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
"""Satori Logging Module Tests."""

import logging as stdlib_logging
import unittest

import mock

from satori.common import logging
from satori.tests import utils


class TestLoggingSetup(utils.TestCase):

    """Logging Setup tests."""

    def test_logging_default_info(self):
        config = {}
        with mock.patch.dict(config, {'logconfig': None}):
            logging.init_logging(config)
            self.assertEqual(stdlib_logging.getLogger().level,
                            stdlib_logging.INFO)

    def test_logging_debug_flag(self):
        #config = mock.MagicMock(logconfig=None, debug=True)
        config = {}
        with mock.patch.dict(config, {'logconfig': None, 'debug': True}):
            logging.init_logging(config)
            self.assertEqual(stdlib_logging.getLogger().level,
                            stdlib_logging.DEBUG)

    def test_logging_verbose_flag(self):
        config = {}
        with mock.patch.dict(config, {'logconfig': None, 'verbose': True}):
            logging.init_logging(config)
            self.assertEqual(stdlib_logging.getLogger().level,
                            stdlib_logging.DEBUG)

    def test_logging_quiet_flag(self):
        config = {}
        with mock.patch.dict(config, {'logconfig': None, 'quiet': True}):
            logging.init_logging(config)
            self.assertEqual(stdlib_logging.getLogger().level,
                            stdlib_logging.WARN)


if __name__ == "__main__":
    unittest.main()
