import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    format="%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s"
)

# Log to file at debug level
file_handler = RotatingFileHandler("notifier.log", backupCount=5)

# TODO Also log at info level to stdout
# TODO Determine log file location
# TODO Find a way to rotate the log, if applicable, after the daily
# channel?
# TODO Add fuckloads more debug logging
