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
"""Logging Module.

This module handles logging to the standard python logging subsystem and to the
console.
"""

from __future__ import absolute_import

import logging
import os
import sys

LOG = logging.getLogger(__name__)


class DebugFormatter(logging.Formatter):

    """Log formatter.

    Outputs any 'data' values passed in the 'extra' parameter if provided.

    **Example**:

    .. code-block:: python

        LOG.debug("My message", extra={'data': locals()})
    """

    def format(self, record):
        """Print out any 'extra' data provided in logs."""
        if hasattr(record, 'data'):
            return "%s. DEBUG DATA=%s" % (logging.Formatter.format(self,
                                          record), record.__dict__['data'])
        return logging.Formatter.format(self, record)


def init_logging(config, default_config=None):
    """Configure logging based on log config file.

    Turn on console logging if no logging files found

    :param config: object with configuration namespace (ex. argparse parser)
    :keyword default_config: path to a python logging configuration file
    """
    if config.get('logconfig') and os.path.isfile(config.get('logconfig')):
        logging.config.fileConfig(config['logconfig'],
                                  disable_existing_loggers=False)
    elif default_config and os.path.isfile(default_config):
        logging.config.fileConfig(default_config,
                                  disable_existing_loggers=False)
    else:
        init_console_logging(config)


def find_console_handler(logger):
    """Return a stream handler, if it exists."""
    for handler in logger.handlers:
        if (isinstance(handler, logging.StreamHandler) and
                handler.stream == sys.stderr):
            return handler


def log_level(config):
    """Get debug settings from configuration.

    --debug: turn on additional debug code/inspection (implies
             logging.DEBUG)
    --verbose: turn up logging output (logging.DEBUG)
    --quiet: turn down logging output (logging.WARNING)
    default is logging.INFO

    :param config: object with configuration namespace (ex. argparse parser)
    """
    if config.get('debug') is True:
        return logging.DEBUG
    elif config.get('verbose') is True:
        return logging.DEBUG
    elif config.get('quiet') is True:
        return logging.WARNING
    else:
        return logging.INFO


def get_debug_formatter(config):
    """Get debug formatter based on configuration.

    :param config: configuration namespace (ex. argparser)

    --debug: log line numbers and file data also
    --verbose: standard debug
    --quiet: turn down logging output (logging.WARNING)
    default is logging.INFO

    :param config: object with configuration namespace (ex. argparse parser)
    """
    if config.get('debug') is True:
        return DebugFormatter('%(pathname)s:%(lineno)d: %(levelname)-8s '
                              '%(message)s')
    elif config.get('verbose') is True:
        return logging.Formatter(
            '%(name)-30s: %(levelname)-8s %(message)s')
    elif config.get('quiet') is True:
        return logging.Formatter('%(message)s')
    else:
        return logging.Formatter('%(message)s')


def init_console_logging(config):
    """Enable logging to the console.

    :param config: object with configuration namespace (ex. argparse parser)
    """
    # define a Handler which writes messages to the sys.stderr
    console = find_console_handler(logging.getLogger())
    if not console:
        console = logging.StreamHandler()
    logging_level = log_level(config)
    console.setLevel(logging_level)

    # set a format which is simpler for console use
    formatter = get_debug_formatter(config)
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger().addHandler(console)
    logging.getLogger().setLevel(logging_level)
    global LOG  # pylint: disable=W0603
    LOG = logging.getLogger(__name__)  # reset
