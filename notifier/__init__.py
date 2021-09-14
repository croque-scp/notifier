import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    format="%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s",
    level="DEBUG",
)

boto3_logger = logging.getLogger("botocore")
boto3_logger.setLevel("INFO")
