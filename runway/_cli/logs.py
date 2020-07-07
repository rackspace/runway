"""Runway CLI logging setup."""
import logging
import os

import coloredlogs

from runway import LogLevels

from ..util import cached_property

# COLOR_FORMAT = "%(levelname)s:%(name)s:\033[%(color)sm%(message)s\033[39m"
LOGGER = logging.getLogger('runway')

LOG_FORMAT = '%(levelname)s:runway:%(message)s'
LOG_FORMAT_VERBOSE = '%(levelname)s:%(name)s:%(message)s'
LOG_FIELD_STYLES = {
    'asctime': {},
    'hostname': {},
    'levelname': {},
    'name': {},
    'programname': {}
}
LOG_LEVEL_STYLES = {
    'critical': {
        'color': 'red',
        'bold': True
    },
    'debug': {
        'color': 'green'
    },
    'error': {
        'color': 'red'
    },
    'info': {},
    'notice': {
        'color': 'yellow'
    },
    'spam': {
        'color': 'green',
        'faint': True
    },
    'success': {
        'color': 'green',
        'bold': True
    },
    'verbose': {
        'color': 'cyan'
    },
    'warning': {
        'color': 214
    }
}


class LogSettings(object):
    """CLI log settings."""

    ENV = {
        'field_styles': os.getenv('COLOREDLOGS_FIELD_STYLES'),
        'fmt': os.getenv('COLOREDLOGS_LOG_FORMAT'),
        'level_styles': os.getenv('COLOREDLOGS_LEVEL_STYLES')
    }

    def __init__(self, debug=0, verbose=False):
        """Instantiate class.

        Args:
            debug (int): Debug level.
            verbose (bool): Whether to display verbose logs.

        """
        self.debug = debug
        self.verbose = verbose

    @property
    def coloredlogs(self):
        """Return settings for coloredlogs.

        Returns:
            Dict[str, Any]

        """
        return {
            'fmt': self.fmt,
            'field_styles': self.field_styles,
            'level_styles': self.level_styles
        }

    @cached_property
    def fmt(self):
        """Return log record format.

        If "COLOREDLOGS_LOG_FORMAT" exists in the environment, it will be used.

        Returns:
            str

        """
        if self.ENV['fmt']:
            return self.ENV['fmt']
        if self.debug or self.verbose:
            return LOG_FORMAT_VERBOSE
        return LOG_FORMAT

    @cached_property
    def field_styles(self):
        """Return log field styles.

        If "COLOREDLOGS_FIELD_STYLES" exists in the environment, it will be
        used to update the Runway LOG_FIELD_STYLES.

        Returns:
            Dict[str, Any]

        """
        result = LOG_FIELD_STYLES.copy()
        if self.ENV['field_styles']:
            result.update(coloredlogs.parse_encoded_styles(
                self.ENV['field_styles']
            ))
        return result

    @cached_property
    def dependency_log_level(self):
        """Return dependency log level.

        Returns:
            LogLevel

        """
        if self.debug > 1:
            return LogLevels.DEBUG
        return LogLevels.ERROR

    @cached_property
    def level_styles(self):
        """Return log level styles.

        If "COLOREDLOGS_LEVEL_STYLES" exists in the environment, it will be
        used to update the Runway LOG_LEVEL_STYLES.

        Returns:
            Dict[str, Any]

        """
        result = LOG_LEVEL_STYLES.copy()
        if self.ENV['level_styles']:
            result.update(coloredlogs.parse_encoded_styles(
                self.ENV['level_styles']
            ))
        return result

    @cached_property
    def runway_log_level(self):
        """Return Runway log level.

        Returns:
            LogLevel

        """
        if self.debug:
            return LogLevels.DEBUG
        if self.verbose:
            return LogLevels.VERBOSE
        return LogLevels.INFO


# TODO implement propper keyword-only args when dropping python 2
def setup_logging(*_, **kwargs):
    """Configure log settings for Runway CLI.

    Keyword Args:
        debug (int): Debug level (0-2).

    """
    settings = LogSettings(debug=kwargs.pop('debug', 0),
                           verbose=kwargs.pop('verbose', False))

    botocore_logger = logging.getLogger('botocore')
    urllib3_logger = logging.getLogger('urllib3')

    coloredlogs.install(settings.runway_log_level, logger=LOGGER,
                        **settings.coloredlogs)
    coloredlogs.install(settings.dependency_log_level,
                        logger=botocore_logger, **settings.coloredlogs)
    coloredlogs.install(settings.dependency_log_level,
                        logger=urllib3_logger, **settings.coloredlogs)
    LOGGER.debug('runway log level: %s', LOGGER.getEffectiveLevel().name)
    LOGGER.debug('dependency log levels: %s', {
        'botocore': botocore_logger.getEffectiveLevel(),
        'urllib3': urllib3_logger.getEffectiveLevel()
    })
    LOGGER.debug('initalized logging for Runway')
