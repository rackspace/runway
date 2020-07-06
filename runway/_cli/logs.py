"""Runway CLI logging setup."""
import logging

import coloredlogs

from runway import LogLevels

# COLOR_FORMAT = "%(levelname)s:%(name)s:\033[%(color)sm%(message)s\033[39m"
LOGGER = logging.getLogger('runway')

LOG_FORMAT = '%(name)s: %(message)s'
LOG_FORMAT_W_LEVEL = '[%(levelname)s]%(name)s: %(message)s'
LOG_FIELD_STYLES = {
    'asctime': {
        'color': 'green'
    },
    'hostname': {
        'color': 'magenta'
    },
    'levelname': {
        # 'color': 'black',
        # 'bold': True
    },
    'name': {},
    'programname': {
        'color': 'cyan'
    }
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
        'color': 'magenta'
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
        'color': 'yellow'
    }
}


# TODO implement propper keyword-only args when dropping python 2
# def setup_logging(*: Any, debug: int) -> None:
def setup_logging(_=None, **kwargs):
    """Configure log settings for Runway CLI.

    Args:
        debug (int): Debug level (0-2).

    """
    debug = kwargs.pop('debug', 0)
    log_settings = {
        'fmt': LOG_FORMAT_W_LEVEL,
        'field_styles': LOG_FIELD_STYLES,
        'level_styles': LOG_LEVEL_STYLES
    }
    runway_log_level = LogLevels.INFO if not debug else LogLevels.DEBUG
    dependency_log_level = LogLevels.ERROR if debug < 2 else LogLevels.DEBUG

    coloredlogs.install(runway_log_level, logger=LOGGER, **log_settings)
    coloredlogs.install(dependency_log_level,
                        logger=logging.getLogger('botocore'), **log_settings)
    coloredlogs.install(dependency_log_level,
                        logger=logging.getLogger('urllib3'), **log_settings)
    LOGGER.debug('inatalized logging for Runway')
