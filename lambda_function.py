from notifier.config.local import read_local_auth, read_local_config
from notifier.main import main


def lambda_handler(event, context):
    """Handler for an AWS Lambda.

    :param event: A list of config paths. First item is the path to the
    main config, second item is the path to the authentication config. This
    must be set in the EventBridge event as a JSON constant.
    """
    del context
    if not isinstance(event, list):
        raise ValueError("Event should be a list of configs")
    if not len(event) == 2:
        raise ValueError("Config list should contain 2 items")
    local_config_path, local_auth_path = event
    main(
        read_local_config(local_config_path),
        read_local_auth(local_auth_path),
    )
