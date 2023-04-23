import json
import logging
import time
from datetime import datetime

import boto3
from dateutil import tz

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.types import ActivationLogDump, LocalConfig

logger = logging.getLogger(__name__)

HALF_AN_HOUR_S = 60 * 30
ONE_DAY_S = 60 * 60 * 24
ENTRY_RETAIN_LIMIT = ONE_DAY_S * 7 * 3


def record_activation_log(
    config: LocalConfig,
    database: BaseDatabaseDriver,
    activation: ActivationLogDump,
) -> None:
    """Records and uploads a notifier activation log."""


def upload_log_dump_to_s3(
    config: LocalConfig,
    database: BaseDatabaseDriver,
    entry_retain_limit: float = ENTRY_RETAIN_LIMIT,
):
    """Uploads an aggregated log dump."""
    # Acquire the dump object from S3
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(config["log_dump_s3"]["bucket_name"])
    dump_object = bucket.Object(config["log_dump_s3"]["object_key"])

    # Construct a log dump from the database
    now = int(time.time())
    timestamp_range = (
        # Add a half hour to the limit to cover any run discrepancies
        # Also handle case where the limit is set to math.inf
        int(max(0, now - (entry_retain_limit + HALF_AN_HOUR_S))),
        now,
    )
    dump = database.get_log_dumps_since(timestamp_range)

    # The Expires header should be set to the end of the current hour
    expiry = datetime.now(tz=tz.gettz("GMT"))
    expiry = expiry.replace(minute=59, second=59, microsecond=0)

    logger.debug(
        "Uploading log dump %s",
        {
            "activation_count": len(dump["activations"]),
            "channel_count": len(dump["channels"]),
            "expires": expiry,
            "timestamp_range": timestamp_range,
        },
    )

    # Upload
    dump_object.put(
        Body=json.dumps(dump).encode("utf-8"),
        ContentType="application/json",
        Expires=expiry,
    )
