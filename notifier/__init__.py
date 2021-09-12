import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    format="%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s",
    level="DEBUG",
)
