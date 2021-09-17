import logging

from notifier.config.local import read_local_auth, read_local_config
from notifier.main import main

# AWS Lambda runtime attaches a default handler with formatting I don't like
# - remove it
rootLogger = logging.getLogger()
if rootLogger.handlers:
    for handler in rootLogger.handlers:
        rootLogger.removeHandler(handler)

# Add my own formatter
logging.basicConfig(
    format="%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def lambda_handler(event, context):
    """Handler for an AWS Lambda.

    :param event: A list of config paths. First item is the path to the
    main config, second item is the path to the authentication config. This
    must be set in the EventBridge event as a JSON constant.
    """
    logger.info("Starting Lambda")
    del context
    if not isinstance(event, list):
        raise ValueError("Event should be a list of configs")
    if not len(event) == 2:
        raise ValueError("Config list should contain 2 items")
    local_config_path, local_auth_path = event
    logger.debug("Lambda: starting main procedure")
    main(
        read_local_config(local_config_path),
        read_local_auth(local_auth_path),
        [],
    )
    logger.info("Lambda finished")
    return 0
