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


def lambda_handler(event, context):
    """Handler for an AWS Lambda.

    :param event: Event parameter passed to the lambda. Expected to contain the
    paths to the config file and auth file. May also contain the start time.
    """
    logger.info("Starting Lambda")
    print("Handler received event:", event)
    del context

    if not isinstance(event, dict):
        raise ValueError("Event should be a dict")

    if "config_path" not in event:
        raise ValueError("Missing key config_path in event")
    local_config_path = event["config_path"]

    if "auth_path" not in event:
        raise ValueError("Missing key auth_path in event")
    local_auth_path = event["auth_path"]

    force_current_time = None
    if "force_current_time" in event:
        force_current_time = event["force_current_time"]

    logger.debug("Lambda: starting main procedure")
    main(
        config=read_local_config(local_config_path),
        auth=read_local_auth(local_auth_path),
        execute_now=[],
        force_current_time=force_current_time,
    )
    logger.info("Lambda finished")
    return 0
