import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler

from misc.colors import rgb, use_color
from misc.config import Config


class ConsoleFormatter(logging.Formatter):
    """Short console lines, coloured by what happened. The log file keeps the full plain format."""
    RESET = '\x1b[0m'
    DIM = rgb(110, 110, 120)
    LEVELS = {logging.DEBUG: rgb(110, 110, 120), logging.INFO: rgb(34, 211, 238), logging.WARNING: rgb(250, 204, 21),
              logging.ERROR: rgb(248, 113, 113, True), logging.CRITICAL: rgb(248, 113, 113, True)}
    LINES = [  # first match wins: (message pattern, colour for the line)
        (re.compile(r'^ADDED\b'), rgb(34, 245, 200, True)),
        (re.compile(r'^ADDING:'), rgb(74, 222, 128)),
        (re.compile(r'^(ADDING \d+|SKIPPED Trakt|Automatic .* task|Added \d+|Anticipation:)'), rgb(255, 43, 214, True)),
        (re.compile(r'^(SKIPP(ING|ED)|dry-run)'), rgb(150, 150, 160)),
        (re.compile(r'(FAILED|Abort|[Ff]ailure|[Ee]xception)'), rgb(248, 113, 113, True)),
        (re.compile(r'^(Validated|\.\.\.Validated|Retrieved|Removed|Sorted|Processing)'), rgb(155, 92, 255)),
    ]
    TITLE = re.compile(r"'([^']+ \(\d{4}\))'")

    def __init__(self, color):
        super().__init__()
        self.color = color

    def format(self, record):
        message = record.getMessage()
        when = self.formatTime(record, '%H:%M:%S')
        level = record.levelname[:5]
        if self.color:
            line = next((c for rx, c in self.LINES if rx.search(message)), '')
            if line:
                message = self.TITLE.sub(lambda m: "%s'%s'%s%s" % ('\x1b[1m', m.group(1), self.RESET, line), message)
            message = '%s%s %s%-5s%s %s%s%s' % (self.DIM, when, self.LEVELS.get(record.levelno, ''), level, self.RESET,
                                                line, message, self.RESET)
        else:
            message = '%s %-5s %s' % (when, level, message)
        if record.exc_info:
            message += '\n' + self.formatException(record.exc_info)
        return message


class Logger:
    def __init__(self, file_name=None, log_level=logging.DEBUG,
                 log_format='%(asctime)s - %(levelname)-10s - %(name)-35s - %(funcName)-35s - %(message)s'):
        self.log_format = log_format

        # init root_logger
        self.log_formatter = logging.Formatter(log_format)
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(log_level)

        # disable bloat loggers
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.ERROR)
        logging.getLogger('schedule').setLevel(logging.ERROR)

        # init console_logger
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setFormatter(ConsoleFormatter(use_color()))
        self.root_logger.addHandler(self.console_handler)

        # init file_logger
        if file_name:
            if os.path.sep not in file_name:
                # file_name was a filename, lets build a full file_path
                self.log_file_path = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), file_name)
            else:
                self.log_file_path = file_name

            self.file_handler = RotatingFileHandler(
                self.log_file_path,
                maxBytes=1024 * 1024 * 2,
                backupCount=5
            )
            self.file_handler.setFormatter(self.log_formatter)
            self.root_logger.addHandler(self.file_handler)

        # Set chosen logging level
        self.root_logger.setLevel(log_level)

    def get_logger(self, name):
        return self.root_logger.getChild(name)


# Default logger
logger = Logger(Config().logfile, logging.DEBUG if Config().cfg.core.debug else logging.INFO)
